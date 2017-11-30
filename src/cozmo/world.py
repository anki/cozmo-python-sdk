# Copyright (c) 2016-2017 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''The "world" represents the robot's known view of its environment.

This view includes objects, faces and pets it knows about and can currently
"see" with its camera, along with what actions or behaviors the robot is
current performing and the images coming back from the camera (if any).

Almost all events emitted by the robot itself, objects, faces, pets and the
camera can be observed directly on the :class:`World` object, which is
itself accessible as :attr:`cozmo.robot.Robot.world`.

For example, if you only need to know whether a particular cube has been
tapped, you can call the :meth:`~cozmo.event.Dispatcher.wait_for` method
directly on that cube's :class:`cozmo.objects.LightCube` instance.  Eg::

    my_cube.wait_for(cozmo.objects.EvtObjectTapped)

If, however, you want to wait for any cube to be tapped, you could instead
call the :meth:`~cozmo.event.Dispatcher.wait_for` method on the
:class:`World` object instead.  Eg::

    robot.world.wait_for(cozmo.objects.EvtObjectTapped)

In either case, ``wait_for`` will return the instance of the event's
:class:`~cozmo.objects.EvtObjectTapped` class, which includes a
:attr:`~cozmo.objects.EvtObjectTapped.obj` attribute, which identifies
exactly which cube has been tapped.

The :class:`World` object also has a :class:`cozmo.camera.Camera` instance
associated with it.  It emits :class:`EvtNewCameraImage` objects whenever
a new camera image is available (generally up to 15 times per second),
which includes the raw image from the camera, as well as an annotated version
showing where faces, pets and objects have been observed.

.. Note::  The camera must first be enabled to receive images by setting
    :attr:`~cozmo.camera.Camera.image_stream_enabled` to ``True``.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['EvtNewCameraImage',
           'CameraImage', 'World']

import asyncio
import collections
import time

from . import logger

from . import annotate
from . import event
from . import faces
from . import nav_memory_map
from . import objects
from . import pets
from . import util

from . import _clad
from ._clad import _clad_to_engine_iface, _clad_to_game_cozmo


class EvtNewCameraImage(event.Event):
    '''Dispatched when a new camera image is received and processed from the robot's camera.'''
    image = 'A CameraImage object'


class World(event.Dispatcher):
    '''Represents the state of the world, as known to a Cozmo robot.'''

    #: callable: The factory function that returns a
    #: :class:`faces.Face` class or subclass instance.
    face_factory = faces.Face

    #: callable: The factory function that returns a
    #: :class:`pets.Pet` class or subclass instance.
    pet_factory = pets.Pet

    #: callable: The factory function that returns an
    #: :class:`objects.LightCube` class or subclass instance.
    light_cube_factory = objects.LightCube

    #: callable: The factory function that returns an
    #: :class:`objects.Charger` class or subclass instance.
    charger_factory = objects.Charger

    #: callable: The factory function that returns an
    #: :class:`objects.CustomObject` class or subclass instance.
    custom_object_factory = objects.CustomObject

    #: callable: The factory function that returns an
    #: :class:`annotate.ImageAnnotator` class or subclass instance.
    annotator_factory = annotate.ImageAnnotator

    def __init__(self, conn, robot, **kw):
        """
        @type conn: cozmo.conn.CozmoConnection
        @type robot: cozmo.robot.Robot
        """
        super().__init__(**kw)
        #: :class:`cozmo.conn.CozmoConnection`: The underlying connection to a device.
        self.conn = conn

        #: :class:`cozmo.annotate.ImageAnnotator`: The image annotator used
        #: to add annotations to the raw camera images.
        self.image_annotator = self.annotator_factory(self)

        #: :class:`cozmo.robot.Robot`: The primary robot
        self.robot = robot  # type: cozmo.robot.Robot

        self.custom_objects = {}

        #: :class:`CameraImage`: The latest image received, or None.
        self.latest_image = None  # type: CameraImage

        self.light_cubes = {}

        #: :class:`cozmo.objects.Charger`: Cozmo's charger.
        #: ``None`` if no charger connected or known about yet.
        self.charger = None  # type: cozmo.objects.Charger

        self._last_image_number = -1
        self._objects = {}
        self._visible_object_counts = collections.defaultdict(int)
        self._visible_face_count = 0
        self._visible_pet_count = 0
        self._faces = {}
        self._pets = {}
        self._active_behavior = None
        self._active_action = None
        self._nav_memory_map = None  # type: nav_memory_map.NavMemoryMapGrid
        self._pending_nav_memory_map = None  # type: nav_memory_map.NavMemoryMapGrid
        self._init_light_cubes()


    #### Private Methods ####

    def _init_light_cubes(self):
        # Initialize 3 cubes, but don't assign object IDs yet - they aren't
        # fixed and will be sent over from the Engine on connection for any
        # connected / known cubes.
        self.light_cubes = {
            objects.LightCube1Id: self.light_cube_factory(objects.LightCube1Id, self.conn, self, dispatch_parent=self),
            objects.LightCube2Id: self.light_cube_factory(objects.LightCube2Id, self.conn, self, dispatch_parent=self),
            objects.LightCube3Id: self.light_cube_factory(objects.LightCube3Id, self.conn, self, dispatch_parent=self),
        }

    def _allocate_object_from_msg(self, msg):
        if msg.objectFamily == _clad_to_game_cozmo.ObjectFamily.LightCube:
            cube = self.light_cubes.get(msg.objectType)
            if not cube:
                logger.error('Received invalid cube objecttype=%s msg=%s', msg.objectType, msg)
                return
            cube.object_id = msg.objectID
            self._objects[cube.object_id] = cube
            cube._robot = self.robot # XXX this will move if/when we have multi-robot support
            logger.debug('Allocated object_id=%d to light cube %s', msg.objectID, cube)
            return cube

        elif msg.objectFamily == _clad_to_game_cozmo.ObjectFamily.Charger:
            charger = self.charger_factory(self.conn, self, msg.objectID, dispatch_parent=self)
            if self.charger:
                logger.error('Allocating multiple chargers: existing charger=%s msg=%s', self.charger, msg)
            self.charger = charger
            self._objects[charger.object_id] = charger
            charger._robot = self.robot  # XXX this will move if/when we have multi-robot support
            logger.debug('Allocated object_id=%s to Charger %s', msg.objectID, charger)
            return charger

        elif msg.objectFamily == _clad_to_game_cozmo.ObjectFamily.CustomObject:
            # obj is the base object type for this custom object. We make instances of this for every
            # unique object_id we see of this custom object type.
            obj = self.custom_objects.get(msg.objectType)
            if not obj:
                logger.error('Received a custom object type: %s that has not been defined yet. Msg=%s' %
                                                                                (msg.objectType, msg))
                return
            custom_object = self.custom_object_factory(self.conn, self, obj.object_type,
                                                       obj.x_size_mm, obj.y_size_mm, obj.z_size_mm,
                                                       obj.marker_width_mm, obj.marker_height_mm,
                                                       obj.is_unique, dispatch_parent=self)
            custom_object.object_id = msg.objectID
            self._objects[custom_object.object_id] = custom_object
            logger.debug('Allocated object_id=%s to CustomObject %s', msg.objectID, custom_object)
            return custom_object

    def _allocate_face_from_msg(self, msg):
        face = self.face_factory(self.conn, self, self.robot, dispatch_parent=self)
        face.face_id = msg.faceID
        self._faces[face.face_id] = face
        logger.debug('Allocated face_id=%s to face=%s', face.face_id, face)
        return face

    def _allocate_pet_from_msg(self, msg):
        pet = self.pet_factory(self.conn, self, self.robot, dispatch_parent=self)
        pet.pet_id = msg.petID
        self._pets[pet.pet_id] = pet
        logger.debug('Allocated pet_id=%s to pet=%s', pet.pet_id, pet)
        return pet

    def _update_visible_obj_count(self, obj, inc):
        obscls = objects.ObservableObject

        for cls in obj.__class__.__mro__:
            self._visible_object_counts[cls] += inc
            if cls == obscls:
                break

    #### Properties ####

    @property
    def active_behavior(self):
        '''bool: True if the robot is currently executing a behavior.'''
        return self._active_behavior

    @property
    def active_action(self):
        '''bool: True if Cozmo is currently executing an action.'''
        return self._active_action

    @property
    def visible_objects(self):
        '''generator: yields each object that Cozmo can currently see.

        For faces, see :meth:`visible_faces`.
        For pets, see :meth:`visible_pets`.

        Returns:
            A generator yielding :class:`cozmo.objects.BaseObject` instances
        '''
        for id, obj in self._objects.items():
            if obj.is_visible:
                yield obj

    def visible_object_count(self, object_type=None):
        '''Returns the number of objects that Cozmo can currently see.

        Args:
            object_type (:class:`~cozmo.objects.ObservableObject` subclass):
                Which type of object to count.  If None, return the total
                number of currently visible objects.
        Returns:
            int: The number of objects that Cozmo can currently see.
        '''
        if object_type is None:
            object_type = objects.ObservableObject
        return self._visible_object_counts[object_type]

    @property
    def visible_faces(self):
        '''generator: yields each face that Cozmo can currently see.

        Returns:
            A generator yielding :class:`cozmo.faces.Face` instances
        '''
        for obj in self._faces.values():
            if obj.is_visible:
                yield obj

    def visible_face_count(self):
        '''Returns the number of faces that Cozmo can currently see.

        Returns:
            int: The number of faces currently visible.
        '''
        return self._visible_face_count

    @property
    def visible_pets(self):
        '''generator: yields each pet that Cozmo can currently see.

        Returns:
            A generator yielding :class:`cozmo.pets.Pet` instances
        '''
        for obj in self._pets.values():
            if obj.is_visible:
                yield obj

    def visible_pet_count(self):
        '''Returns the number of pets that Cozmo can currently see.

        Returns:
            int: The number of pets currently visible.
        '''
        return self._visible_pet_count

    def get_light_cube(self, cube_id):
        """Returns the light cube with the given cube ID
                
        Args:
            cube_id (int): The light cube ID - should be one of
                :attr:`~cozmo.objects.LightCube1Id`,
                :attr:`~cozmo.objects.LightCube2Id` and
                :attr:`~cozmo.objects.LightCube3Id`. Note: the cube_id is not
                the same thing as the object_id.
        Returns:
            :class:`cozmo.objects.LightCube`: The LightCube object with that cube_id
        
        Raises:
            :class:`ValueError` if the cube_id is invalid.
        """
        if cube_id not in objects.LightCubeIDs:
            raise ValueError("Invalid cube_id %s" % cube_id)
        cube = self.light_cubes.get(cube_id)
        # Only return the cube if it has an object_id
        if cube.object_id is not None:
            return cube
        return None

    @property
    def connected_light_cubes(self):
        '''generator: yields each LightCube that Cozmo is currently connected to.

        Returns:
            A generator yielding :class:`cozmo.objects.LightCube` instances
        '''
        for cube_id in objects.LightCubeIDs:
            cube = self.light_cubes.get(cube_id)
            if cube and cube.is_connected:
                yield cube

    @property
    def nav_memory_map(self):
        """Returns the latest navigation memory map for Cozmo.
        
        Returns:
             :class:`~cozmo.nav_memory_map.NavMemoryMapGrid`: Current navigation
                memory map. This will be none unless you've previously called
                :meth:`~cozmo.world.request_nav_memory_map` with a positive
                frequency to request the data be sent over from the engine.
        """
        return self._nav_memory_map

    #### Private Event Handlers ####

    def _recv_msg_robot_observed_object(self, evt, *, msg):
        #The engine still sends observed messages for fixed custom objects, this is a bug
        if evt.msg.objectType == _clad_to_game_cozmo.ObjectType.CustomFixedObstacle:
            return
        obj = self._objects.get(msg.objectID)
        if not obj:
            obj = self._allocate_object_from_msg(msg)
        if obj:
            obj.dispatch_event(evt)

    def _recv_msg_robot_observed_face(self, evt, *, msg):
        if msg.faceID < 0:
            # this face is being tracked, but is not yet recognized - ignore
            return
        face = self._faces.get(msg.faceID)
        if not face:
            face = self._allocate_face_from_msg(msg)
        if face:
            face.dispatch_event(evt)

    def _recv_msg_robot_changed_observed_face_id(self, evt, *, msg):
        old_face = self._faces.get(msg.oldID)
        if old_face:
            old_face.dispatch_event(evt)

    def _recv_msg_robot_renamed_enrolled_face(self, evt, *, msg):
        face = self._faces.get(msg.faceID)
        if face:
            face.dispatch_event(evt)

    def _recv_msg_robot_erased_enrolled_face(self, evt, *, msg):
        face = self._faces.get(msg.faceID)
        if face:
            face.dispatch_event(evt)

    def _recv_msg_robot_observed_pet(self, evt, *, msg):
        pet = self._pets.get(msg.petID)
        if not pet:
            pet = self._allocate_pet_from_msg(msg)
        if pet:
            pet.dispatch_event(evt)

    def _dispatch_object_event(self, evt, msg):
        obj = self._objects.get(msg.objectID)
        if not obj:
            logger.warning('%s event received for unknown object ID %s', type(msg).__name__, msg.objectID)
            return
        obj.dispatch_event(evt)

    def _recv_msg_object_tapped(self, evt, *, msg):
        self._dispatch_object_event(evt, msg)

    def _recv_msg_object_moved(self, evt, *, msg):
        self._dispatch_object_event(evt, msg)

    def _recv_msg_object_stopped_moving(self, evt, *, msg):
        self._dispatch_object_event(evt, msg)

    def _recv_msg_object_power_level(self, evt, *, msg):
        self._dispatch_object_event(evt, msg)

    def _recv_msg_object_connection_state(self, evt, *, msg):
        self._dispatch_object_event(evt, msg)

    def _recv_msg_connected_object_states(self, evt, *, msg):
        # This is received on startup as a response to RequestConnectedObjects.
        for object_state in msg.objects:
            obj = self._objects.get(object_state.objectID)
            if not obj:
                obj = self._allocate_object_from_msg(object_state)
            if obj:
                obj._handle_connected_object_state(object_state)

    def _recv_msg_located_object_states(self, evt, *, msg):
        # This is received on startup as a response to RequestLocatedObjectStates.
        # It's also automatically sent from Engine whenever poses are rejiggered.
        updated_objects = set()
        for object_state in msg.objects:
            obj = self._objects.get(object_state.objectID)
            if not obj:
                obj = self._allocate_object_from_msg(object_state)
            if obj:
                obj._handle_located_object_state(object_state)
            updated_objects.add(object_state.objectID)
        # ensure that all objects not received have invalidated poses
        for id, obj in self._objects.items():
            if (id not in updated_objects) and obj.pose.is_valid:
                obj.pose.invalidate()

    def _recv_msg_robot_deleted_located_object(self, evt, *, msg):
        obj = self._objects.get(msg.objectID)
        if obj is None:
            logger.warning("Ignoring deleted_located_object for unknown object ID %s", msg.objectID)
        else:
            logger.debug("Invalidating pose for deleted located object %s" % obj)
            obj.pose.invalidate()

    def _recv_msg_robot_delocalized(self, evt, *, msg):
        # Invalidate the pose for every object
        logger.info("Robot delocalized - invalidating poses for all objects")
        for obj in self._objects.values():
            obj.pose.invalidate()

    def _recv_msg_memory_map_message_begin(self, evt, *, msg):
        if self._pending_nav_memory_map is not None:
            logger.error("NavMemoryMap unexpected begin - restarting map")
        self._pending_nav_memory_map = nav_memory_map.NavMemoryMapGrid(
                                            msg.originId, msg.rootDepth,
                                            msg.rootSize_mm, msg.rootCenterX,
                                            msg.rootCenterY)

    def _recv_msg_memory_map_message(self, evt, *, msg):
        if self._pending_nav_memory_map is not None:
            for quad in msg.quadInfos:
                self._pending_nav_memory_map._add_quad(quad.content, quad.depth)
        else:
            logger.error("NavMemoryMap message without begin - ignoring")

    def _recv_msg_memory_map_message_end(self, evt, *, msg):
        if self._pending_nav_memory_map is not None:
            # The pending map is now the latest complete map
            self._nav_memory_map = self._pending_nav_memory_map
            self._pending_nav_memory_map = None
            self.dispatch_event(nav_memory_map.EvtNewNavMemoryMap,
                                nav_memory_map=self._nav_memory_map)
        else:
            logger.error("NavMemoryMap end without begin - ignoring")

    #### Public Event Handlers ####

    def recv_evt_object_tapped(self, event, *, obj, tap_count, tap_duration, **kw):
        pass

    def recv_evt_behavior_started(self, evt, *, behavior, **kw):
        self._active_behavior = behavior

    def recv_evt_behavior_stopped(self, evt, *, behavior, **kw):
        self._active_behavior = None

    def recv_evt_action_started(self, evt, *, action, **kw):
        self._active_action = action

    def recv_evt_action_completed(self, evt, *, action, **kw):
        self._active_action = None

    def recv_evt_new_raw_camera_image(self, evt, *, image, **kw):
        self._last_image_number += 1
        processed_image = CameraImage(image, self.image_annotator, self._last_image_number)
        self.latest_image = processed_image
        self.dispatch_event(EvtNewCameraImage, image=processed_image)

    def recv_evt_object_appeared(self, evt, *, obj, **kw):
        self._update_visible_obj_count(obj, 1)

    def recv_evt_object_vanished(self, evt, *, obj, **kw):
        self._update_visible_obj_count(obj, -1)

    def recv_evt_face_appeared(self, evt, *, face, **kw):
        self._visible_face_count += 1

    def recv_evt_face_disappeared(self, evt, *, face, **kw):
        self._visible_face_count -= 1

    def recv_evt_pet_appeared(self, evt, *, pet, **kw):
        self._visible_pet_count += 1

    def recv_evt_pet_disappeared(self, evt, *, pet, **kw):
        self._visible_pet_count -= 1


    #### Event Wrappers ####

    def _find_visible_object(self, object_type):
        for visible_object in self.visible_objects:
            if (object_type is None) or isinstance(visible_object, object_type):
                return visible_object
        return None

    async def wait_for_observed_light_cube(self, timeout=None, include_existing=True):
        '''Waits for one of the light cubes to be observed by the robot.

        Args:
            timeout (float): Number of seconds to wait for a cube to be
                observed, or None for indefinite
            include_existing (bool): Specifies whether to include light cubes
                that are already visible.
        Returns:
            The :class:`cozmo.objects.LightCube` object that was observed.
        '''
        if include_existing:
            obj = self._find_visible_object(objects.LightCube)
            if obj:
                return obj

        filter = event.Filter(objects.EvtObjectObserved,
                obj=lambda obj: isinstance(obj, objects.LightCube))
        evt = await self.wait_for(filter, timeout=timeout)
        return evt.obj

    async def wait_for_observed_face(self, timeout=None, include_existing=True):
        '''Waits for a face to be observed by the robot.

        Args:
            timeout (float): Number of seconds to wait for a face to be
                observed, or None for indefinite
            include_existing (bool): Specifies whether to include faces
                that are already visible.
        Returns:
            The :class:`cozmo.faces.Face` object that was observed.
        '''
        if include_existing:
            face = next(self.visible_faces, None)
            if face:
                return face

        filter = event.Filter(faces.EvtFaceObserved)
        evt = await self.wait_for(filter, timeout=timeout)
        return evt.face

    async def wait_for_observed_pet(self, timeout=None, include_existing=True):
        '''Waits for a pet to be observed by the robot.

        Args:
            timeout (float): Number of seconds to wait for a pet to be
                observed, or None for indefinite
            include_existing (bool): Specifies whether to include pets
                that are already visible.
        Returns:
            The :class:`cozmo.pets.Pet` object that was observed.
        '''
        if include_existing:
            pet = next(self.visible_pets, None)
            if pet:
                return pet

        filter = event.Filter(pets.EvtPetObserved)
        evt = await self.wait_for(filter, timeout=timeout)
        return evt.pet

    async def wait_for_observed_charger(self, timeout=None, include_existing=True):
        '''Waits for a charger to be observed by the robot.

        Args:
            timeout (float): Number of seconds to wait for a charger to be
                observed, or None for indefinite
            include_existing (bool): Specifies whether to include chargers
                that are already visible.
        Returns:
            The :class:`cozmo.objects.Charger` object that was observed.
        '''
        if include_existing:
            obj = self._find_visible_object(objects.Charger)
            if obj:
                return obj

        filter = event.Filter(objects.EvtObjectObserved,
                obj=lambda obj: isinstance(obj, objects.Charger))
        evt = await self.wait_for(filter, timeout=timeout)
        return evt.obj

    async def wait_until_observe_num_objects(self, num, object_type=None, timeout=None,
                                             include_existing=True):
        '''Waits for a certain number of unique objects to be seen at least once.

        This method waits for a number of unique objects to be seen, but not
        necessarily concurrently.  That is, if cube 1 appears to the camera and
        then moves out of view to be replaced by cube 2, then that will count
        as 2 observed objects.

        To wait for multiple objects to be visible simultaneously, see
        :meth:`wait_until_num_objects_visible`.

        Args:
            num (float): The number of unique objects to wait for.
            object_type (class:`cozmo.objects.ObservableObject`): If provided
                this will cause only the selected object types to be counted.
            timeout (float): Maximum amount of time in seconds to wait for the
                requested number of objects to be observed.
            include_existing (bool): Specifies whether to include objects
                that are already visible.
        Returns:
            A list of length <= num of the unique objects
            class:`cozmo.objects.ObservableObject` observed during this wait.
        '''
        #Filter by object type if provided
        filter = objects.EvtObjectAppeared
        if object_type:
            if not issubclass(object_type, objects.ObservableObject):
                raise TypeError("Expected object_type to be ObservableObject")
            filter = event.Filter(objects.EvtObjectAppeared,
                    obj=lambda obj: isinstance(obj, object_type))

        objs_seen = set()
        # If requested, add any objects that can already be seen (they won't create observed events)
        if include_existing:
            for visible_object in self.visible_objects:
                if (object_type is None) or isinstance(visible_object, object_type):
                    objs_seen.add(visible_object)

        #Wait until we see a certain number of unique objects
        timeout = util.Timeout(timeout)
        while len(objs_seen) < num and not timeout.is_timed_out:
            try:
                evt = await self.wait_for(filter, timeout=timeout.remaining)
                objs_seen.add(evt.obj)
            except asyncio.TimeoutError:
                # on timeout, return the set of objects seen so far.
                return list(objs_seen)
        return list(objs_seen)

    async def wait_until_num_objects_visible(self, num, object_type=None, timeout=None):
        '''Waits for at least a specific number of objects to be seen concurrently.

        Unlike :meth:`wait_until_observe_num_objects` which returns when
        several objects have become visible, but not necessarily
        simultaneously, this method will only return if the specific
        number of objects are visible to the camera at the same time
        (as defined by :const:`objects.OBJECT_VISIBILITY_TIMEOUT`).

        Args:
            num (float): The number of unique objects to wait for.
            object_type (class:`cozmo.objects.ObservableObject`): If provided
                this will cause only the selected object types to be counted.
            timeout (float): Maximum amount of time in seconds to wait for the
                requested number of objects to be observed.
        Returns:
            int: The number of objects seen (num or higher).
        Raises:
            asyncio.TimeoutError if the required count wasn't seen.
        '''
        count = self.visible_object_count(object_type)
        timeout = util.Timeout(timeout)
        while count < num and not timeout.is_timed_out:
            await self.wait_for(objects.EvtObjectAppeared, timeout=timeout.remaining)
            count = self.visible_object_count(object_type)

        if count < num:
            raise asyncio.TimeoutError()
        return count


    #### Commands ####

    def send_available_objects(self):
        # XXX description for this?
        msg = _clad_to_engine_iface.SendAvailableObjects(enable=True)
        self.conn.send_msg(msg)

    def _remove_custom_marker_object_instances(self):
        for id, obj in list(self._objects.items()):
            if isinstance(obj, objects.CustomObject):
                logger.info("Removing CustomObject instance: id %s = obj '%s'", id, obj)
                del self._objects[id]

    def _remove_fixed_custom_object_instances(self):
        for id, obj in list(self._objects.items()):
            if isinstance(obj, objects.FixedCustomObject):
                logger.info("Removing FixedCustomObject instance: id %s = obj '%s'", id, obj)
                del self._objects[id]

    async def delete_all_custom_objects(self):
        """Causes the robot to forget about all custom (fixed + marker) objects it currently knows about.
        
        Note: This includes all fixed custom objects, and all custom marker object instances, 
        BUT this does NOT remove the custom marker object definitions, so Cozmo
        will continue to add new objects if he sees the markers again. To remove
        the definitions for those objects use: :meth:`undefine_all_custom_marker_objects`
        """
        msg = _clad_to_engine_iface.DeleteAllCustomObjects()
        self.conn.send_msg(msg)
        # suppression for _MsgRobotDeletedAllCustomObjects "no-member" on pylint
        #pylint: disable=no-member
        await self.wait_for(_clad._MsgRobotDeletedAllCustomObjects)
        self._remove_custom_marker_object_instances()
        self._remove_fixed_custom_object_instances()

    async def delete_custom_marker_objects(self):
        """Causes the robot to forget about all custom marker objects it currently knows about.

        Note: This removes custom marker object instances only, it does NOT remove
        fixed custom objects, nor does it remove the custom marker object definitions, so Cozmo
        will continue to add new objects if he sees the markers again. To remove
        the definitions for those objects use: :meth:`undefine_all_custom_marker_objects`
        """
        msg = _clad_to_engine_iface.DeleteCustomMarkerObjects()
        self.conn.send_msg(msg)
        #pylint: disable=no-member
        await self.wait_for(_clad._MsgRobotDeletedCustomMarkerObjects)
        self._remove_custom_marker_object_instances()

    async def delete_fixed_custom_objects(self):
        """Causes the robot to forget about all fixed custom objects it currently knows about.

        Note: This removes fixed custom objects only, it does NOT remove
        the custom marker object instances or definitions.
        """
        msg = _clad_to_engine_iface.DeleteFixedCustomObjects()
        self.conn.send_msg(msg)
        #pylint: disable=no-member
        await self.wait_for(_clad._MsgRobotDeletedFixedCustomObjects)
        self._remove_fixed_custom_object_instances()

    async def undefine_all_custom_marker_objects(self):
        """Remove all custom marker object definitions, and any instances of them in the world."""
        msg = _clad_to_engine_iface.UndefineAllCustomMarkerObjects()
        self.conn.send_msg(msg)
        #pylint: disable=no-member
        await self.wait_for(_clad._MsgRobotDeletedCustomMarkerObjects)
        self._remove_custom_marker_object_instances()
        # Remove all custom object definitions / archetypes
        self.custom_objects.clear()

    async def _wait_for_defined_custom_object(self, custom_object_archetype):
        try:
            #pylint: disable=no-member
            msg = await self.wait_for(_clad._MsgDefinedCustomObject, timeout=5)
        except asyncio.TimeoutError as e:
            logger.error("Failed (Timed Out) to define: %s", custom_object_archetype)
            return None

        msg = msg.msg  # get the internal message
        if msg.success:
            type_id = custom_object_archetype.object_type.id
            self.custom_objects[type_id] = custom_object_archetype
            logger.info("Defined: %s", custom_object_archetype)
            return custom_object_archetype
        else:
            logger.error("Failed to define Custom Object %s", custom_object_archetype)
            return None

    async def define_custom_box(self, custom_object_type,
                                marker_front, marker_back,
                                marker_top, marker_bottom,
                                marker_left, marker_right,
                                depth_mm, width_mm, height_mm,
                                marker_width_mm, marker_height_mm,
                                is_unique=True):
        '''Defines a cuboid of custom size and binds it to a specific custom object type.

        The engine will now detect the markers associated with this object and send an
        object_observed message when they are seen. The markers must be placed in the center
        of their respective sides. All 6 markers must be unique.

        Args:
            custom_object_type (:class:`cozmo.objects.CustomObjectTypes`): the
                object type you are binding this custom object to
            marker_front (:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to the front of the object
            marker_back (:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to the back of the object
            marker_top (:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to the top of the object
            marker_bottom (:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to the bottom of the object
            marker_left (:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to the left of the object
            marker_right (:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to the right of the object
            depth_mm (float): depth of the object (in millimeters) (X axis)
            width_mm (float): width of the object (in millimeters) (Y axis)
            height_mm (float): height of the object (in millimeters) (Z axis)
                (the height of the object)
            marker_width_mm (float): width of the printed marker (in millimeters).
            maker_height_mm (float): height of the printed marker (in millimeters).
            is_unique (bool): If True, the engine will assume there is only 1 of this object
                (and therefore only 1 of each of any of these markers) in the world.

        Returns:
            A :class:`cozmo.object.CustomObject` instance with the specified dimensions.
                This is None if the definition failed internally.
                Note: No instances of this object are added to the world until they have been seen.

        Raises:
            TypeError if the custom_object_type is of the wrong type.
            ValueError if the 6 markers aren't unique.
        '''
        if not isinstance(custom_object_type, objects._CustomObjectType):
            raise TypeError("Unsupported object_type, requires CustomObjectType")

        # verify all 6 markers are unique
        markers = {marker_front, marker_back, marker_top, marker_bottom, marker_left, marker_right}
        if len(markers) != 6:
            raise ValueError("all markers must be unique for a custom box")

        custom_object_archetype = self.custom_object_factory(self.conn, self, custom_object_type,
                                                             depth_mm, width_mm, height_mm,
                                                             marker_width_mm, marker_height_mm,
                                                             is_unique, dispatch_parent=self)

        msg = _clad_to_engine_iface.DefineCustomBox(customType=custom_object_type.id,
                                                    markerFront=marker_front.id,
                                                    markerBack=marker_back.id,
                                                    markerTop=marker_top.id,
                                                    markerBottom=marker_bottom.id,
                                                    markerLeft=marker_left.id,
                                                    markerRight=marker_right.id,
                                                    xSize_mm=depth_mm,
                                                    ySize_mm=width_mm,
                                                    zSize_mm=height_mm,
                                                    markerWidth_mm=marker_width_mm,
                                                    markerHeight_mm=marker_height_mm,
                                                    isUnique=is_unique)

        self.conn.send_msg(msg)

        return await self._wait_for_defined_custom_object(custom_object_archetype)

    async def define_custom_cube(self, custom_object_type,
                                 marker,
                                 size_mm,
                                 marker_width_mm, marker_height_mm,
                                 is_unique=True):
        """Defines a cube of custom size and binds it to a specific custom object type.

        The engine will now detect the markers associated with this object and send an
        object_observed message when they are seen. The markers must be placed in the center
        of their respective sides.

        Args:
            custom_object_type (:class:`cozmo.objects.CustomObjectTypes`): the
                object type you are binding this custom object to.
            marker:(:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to every side of the cube.
            size_mm: size of each side of the cube (in millimeters).
            marker_width_mm (float): width of the printed marker (in millimeters).
            maker_height_mm (float): height of the printed marker (in millimeters).
            is_unique (bool): If True, the engine will assume there is only 1 of this object
                (and therefore only 1 of each of any of these markers) in the world.

        Returns:
            A :class:`cozmo.object.CustomObject` instance with the specified dimensions.
                This is None if the definition failed internally.
                Note: No instances of this object are added to the world until they have been seen.

        Raises:
            TypeError if the custom_object_type is of the wrong type.
        """

        if not isinstance(custom_object_type, objects._CustomObjectType):
            raise TypeError("Unsupported object_type, requires CustomObjectType")

        custom_object_archetype = self.custom_object_factory(self.conn, self, custom_object_type,
                                                             size_mm, size_mm, size_mm,
                                                             marker_width_mm, marker_height_mm,
                                                             is_unique, dispatch_parent=self)

        msg = _clad_to_engine_iface.DefineCustomCube(customType=custom_object_type.id,
                                                     marker=marker.id,
                                                     size_mm=size_mm,
                                                     markerWidth_mm=marker_width_mm,
                                                     markerHeight_mm=marker_height_mm,
                                                     isUnique=is_unique)

        self.conn.send_msg(msg)

        return await self._wait_for_defined_custom_object(custom_object_archetype)

    async def define_custom_wall(self, custom_object_type,
                                 marker,
                                 width_mm, height_mm,
                                 marker_width_mm, marker_height_mm,
                                 is_unique=True):
        """Defines a wall of custom width and height, with a fixed depth of 10mm, and binds it to a specific custom object type.

        The engine will now detect the markers associated with this object and send an
        object_observed message when they are seen. The markers must be placed in the center
        of their respective sides.

        Args:
            custom_object_type (:class:`cozmo.objects.CustomObjectTypes`): the
                object type you are binding this custom object to.
            marker:(:class:`cozmo.objects.CustomObjectMarkers`): the marker
                affixed to the front and back of the wall
            width_mm (float): width of the object (in millimeters). (Y axis).
            height_mm (float): height of the object (in millimeters). (Z axis).
            width_mm: width of the wall (along Y axis) (in millimeters).
            height_mm: height of the wall (along Z axis) (in millimeters).
            marker_width_mm (float): width of the printed marker (in millimeters).
            maker_height_mm (float): height of the printed marker (in millimeters).
            is_unique (bool): If True, the engine will assume there is only 1 of this object
                (and therefore only 1 of each of any of these markers) in the world.

        Returns:
            A :class:`cozmo.object.CustomObject` instance with the specified dimensions.
                This is None if the definition failed internally.
                Note: No instances of this object are added to the world until they have been seen.

        Raises:
            TypeError if the custom_object_type is of the wrong type.
        """

        if not isinstance(custom_object_type, objects._CustomObjectType):
            raise TypeError("Unsupported object_type, requires CustomObjectType")

        # TODO: share this hardcoded constant from engine
        WALL_THICKNESS_MM = 10.0

        custom_object_archetype = self.custom_object_factory(self.conn, self, custom_object_type,
                                                             WALL_THICKNESS_MM, width_mm, height_mm,
                                                             marker_width_mm, marker_height_mm,
                                                             is_unique, dispatch_parent=self)

        msg = _clad_to_engine_iface.DefineCustomWall(customType=custom_object_type.id,
                                                     marker=marker.id,
                                                     width_mm=width_mm,
                                                     height_mm=height_mm,
                                                     markerWidth_mm=marker_width_mm,
                                                     markerHeight_mm=marker_height_mm,
                                                     isUnique=is_unique)

        self.conn.send_msg(msg)

        return await self._wait_for_defined_custom_object(custom_object_archetype)

    async def create_custom_fixed_object(self, pose, x_size_mm, y_size_mm, z_size_mm,
                                         relative_to_robot=False, use_robot_origin=True):
        '''Defines a cuboid of custom size and places it in the world. It cannot be observed.

        Args:
            pose (:class:`cozmo.util.Pose`): The pose of the object we are creating.
            x_size_mm (float): size of the object (in millimeters) in the x axis.
            y_size_mm (float): size of the object (in millimeters) in the y axis.
            z_size_mm (float): size of the object (in millimeters) in the z axis.
            relative_to_robot (bool): whether or not the pose given assumes the robot's pose as its origin.
            use_robot_origin (bool): whether or not to override the origin_id in the given pose to be
                                      the origin_id of Cozmo.

        Returns:
            A :class:`cozmo.objects.FixedCustomObject` instance with the specified dimensions and pose.
        '''
        # Override the origin of the pose to be the same as the robot's. This will make sure they are in
        # the same space in the engine every time.
        if use_robot_origin:
            pose.origin_id = self.robot.pose.origin_id
        # In this case define the given pose to be with respect to the robot's pose as its origin.
        if relative_to_robot:
            pose = self.robot.pose.define_pose_relative_this(pose)
        msg = _clad_to_engine_iface.CreateFixedCustomObject(pose=pose.encode_pose(),
                                                            xSize_mm=x_size_mm, ySize_mm=y_size_mm, zSize_mm=z_size_mm)
        self.conn.send_msg(msg)
        #pylint: disable=no-member
        response = await self.wait_for(_clad._MsgCreatedFixedCustomObject)
        fixed_custom_object = objects.FixedCustomObject(pose, x_size_mm, y_size_mm, z_size_mm, response.msg.objectID)
        self._objects[fixed_custom_object.object_id] = fixed_custom_object
        return fixed_custom_object

    def enable_block_tap_filter(self, enable=True):
        '''Enable or disable the block tap filter in the engine.

        The block (AKA LightCube) tap filter removes low intensity taps, and
        filters out taps that come in rapidly together and instead just sends
        the strongest one

        Args:
            enable (bool): specifies whether the filter should be enabled or disabled
        '''
        msg = _clad_to_engine_iface.EnableBlockTapFilter(enable=enable)
        self.conn.send_msg(msg)

    def disconnect_from_cubes(self):
        """Disconnect from all cubes (to save battery life etc.).
        
        Call :meth:`connect_to_cubes` to re-connect to the cubes later.        
        """
        logger.info("Disconnecting from cubes.")
        for cube in self.connected_light_cubes:
            logger.info("Disconnecting from %s" % cube)

        msg = _clad_to_engine_iface.BlockPoolResetMessage(enable=False,
                                                          maintainPersistentPool=True)
        self.conn.send_msg(msg)

    async def connect_to_cubes(self):
        """Connect to all cubes.
        
        Request that Cozmo connects to all cubes - this is required if you
        previously called :meth:`disconnect_from_cubes` or
        :meth:`auto_disconnect_from_cubes_at_end` with enable=False. Connecting
        to a cube can take up to about 5 seconds, and this method will wait until
        either all 3 cubes are connected, or it has timed out waiting for this.
                
        Returns:
            bool: True if all 3 cubes are now connected.
        """
        connected_cubes = list(self.connected_light_cubes)
        num_connected_cubes = len(connected_cubes)
        num_unconnected_cubes = 3 - num_connected_cubes
        if num_unconnected_cubes < 1:
            logger.info("connect_to_cubes skipped - already connected to %s cubes", num_connected_cubes)
            return True
        logger.info("Connecting to cubes (already connected to %s, waiting for %s)", num_connected_cubes, num_unconnected_cubes)
        for cube in connected_cubes:
            logger.info("Already connected to %s" % cube)

        msg = _clad_to_engine_iface.BlockPoolResetMessage(enable=True,
                                                          maintainPersistentPool=True)
        self.conn.send_msg(msg)

        success = True

        try:
            for _ in range(num_unconnected_cubes):
                #pylint: disable=no-member
                msg = await self.wait_for(_clad._MsgObjectConnectionState, timeout=10)
        except asyncio.TimeoutError as e:
            logger.warning("Failed to connect to all cubes in time!")
            success = False

        if success:
            logger.info("Connected to all cubes!")

        self.conn._request_connected_objects()

        try:
            #pylint: disable=no-member
            msg = await self.wait_for(_clad._MsgConnectedObjectStates, timeout=5)
        except asyncio.TimeoutError as e:
            logger.warning("Failed to receive connected cube states.")
            success = False

        return success

    def auto_disconnect_from_cubes_at_end(self, enable=True):
        """Tell the SDK to auto disconnect from cubes at the end of every SDK program.

        This can be used to save cube battery life if you spend a lot of time in
        SDK mode but aren't running programs as much (as you're busy writing
        them). Call :meth:`connect_to_cubes` to re-connect to the cubes later. 

        Args:
            enable (bool): True if cubes should disconnect after every SDK program exits. 
        """
        msg = _clad_to_engine_iface.SetShouldAutoDisconnectFromCubesAtEnd(doAutoDisconnect=enable)
        self.conn.send_msg(msg)

    def request_nav_memory_map(self, frequency_s):
        """Request navigation memory map data from Cozmo.
                
        The memory map can be accessed via :attr:`~cozmo.world.World.nav_memory_map`,
        it will be None until :meth:`request_nav_memory_map` has been called and
        a map has been received. The memory map provides a quad-tree map of
        where Cozmo thinks there are objects, and where Cozmo thinks it is safe
        to drive.
        
        Args:
            frequency_s (float): number of seconds between each update being sent.
                Negative values, e.g. -1.0, will disable any updates being sent.
        """
        msg = _clad_to_engine_iface.SetMemoryMapBroadcastFrequency_sec(frequency_s)
        self.conn.send_msg(msg)


class CameraImage:
    '''A single image from Cozmo's camera.

    This wraps a raw image and provides an :meth:`annotate_image` method
    that can resize and add dynamic annotations to the image, such as
    marking up the location of objects, faces and pets.
    '''
    def __init__(self, raw_image, image_annotator, image_number=0):
        #: :class:`PIL.Image.Image`: the raw unprocessed image from the camera
        self.raw_image = raw_image

        #: :class:`cozmo.annotate.ImageAnnotator`: the image annotation object
        self.image_annotator = image_annotator

        #: int: An image number that increments on every new image received
        self.image_number = image_number

        #: float: The time the image was received and processed by the SDK
        self.image_recv_time = time.time()

    def annotate_image(self, scale=None, fit_size=None, resample_mode=annotate.RESAMPLE_MODE_NEAREST):
        '''Adds any enabled annotations to the image.

        Optionally resizes the image prior to annotations being applied.  The
        aspect ratio of the resulting image always matches that of the raw image.

        Args:
            scale (float): If set then the base image will be scaled by the
                supplied multiplier.  Cannot be combined with fit_size
            fit_size (tuple of int):  If set, then scale the image to fit inside
                the supplied (width, height) dimensions. The original aspect
                ratio will be preserved.  Cannot be combined with scale.
            resample_mode (int): The resampling mode to use when scaling the
                image. Should be either :attr:`~cozmo.annotate.RESAMPLE_MODE_NEAREST`
                (fast) or :attr:`~cozmo.annotate.RESAMPLE_MODE_BILINEAR` (slower,
                but smoother).
        Returns:
            :class:`PIL.Image.Image`
        '''
        return self.image_annotator.annotate_image(self.raw_image,
                                                   scale=scale,
                                                   fit_size=fit_size,
                                                   resample_mode=resample_mode)
