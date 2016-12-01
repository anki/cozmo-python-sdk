# Copyright (c) 2016 Anki, Inc.
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
        super().__init__(**kw)
        #: :class:`cozmo.conn.CozmoConnection`: The underlying connection to a device.
        self.conn = conn

        #: :class:`cozmo.annotate.ImageAnnotator`: The image annotator used
        #: to add annotations to the raw camera images.
        self.image_annotator = self.annotator_factory(self)

        #: :class:`cozmo.robot.Robot`: The primary robot
        self.robot = robot

        self.custom_objects = {}

        #: :class:`CameraImage`: The latest image received, or None.
        self.latest_image = None

        self.light_cubes = {}

        #: :class:`cozmo.objects.Charger`: Cozmo's charger.
        #: ``None`` if no charger connected or known about yet.
        self.charger = None

        self._last_image_number = -1
        self._objects = {}
        self._visible_object_counts = collections.defaultdict(int)
        self._visible_face_count = 0
        self._visible_pet_count = 0
        self._faces = {}
        self._pets = {}
        self._active_behavior = None
        self._active_action = None
        self._init_light_cubes()


    #### Private Methods ####

    def _init_light_cubes(self):
        # XXX assume that the three cubes exist; haven't yet found an example
        # where this isn't hard-coded.  Smells bad.  Don't allocate an object id
        # i've seen them have an ID of 0 when observed.
        self.light_cubes = {
            objects.LightCube1Id: self.light_cube_factory(self.conn, self, dispatch_parent=self),
            objects.LightCube2Id: self.light_cube_factory(self.conn, self, dispatch_parent=self),
            objects.LightCube3Id: self.light_cube_factory(self.conn, self, dispatch_parent=self),
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
                                                       dispatch_parent=self)
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

    #### Private Event Handlers ####

    def _recv_msg_robot_observed_object(self, evt, *, msg):
        #The engine still sends observed messages for fixed custom objects, this is a bug
        if evt.msg.objectType == _clad_to_game_cozmo.ObjectType.Custom_Fixed:
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

    def _recv_msg_object_tapped(self, evt, *, msg):
        obj = self._objects.get(msg.objectID)
        if not obj:
            logger.warn('Tap event received for unknown object ID %s', msg.objectID)
            return
        obj.dispatch_event(evt)

    def _recv_msg_available_objects(self, evt, *, msg):
        for available_object in msg.objects:
            obj = self._objects.get(available_object.objectID)
            if not obj:
                obj = self._allocate_object_from_msg(available_object)
            if obj:
                obj._handle_available_object(available_object)

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
        msg = _clad_to_engine_iface.SendAvailableObjects(
                robotID=self.robot.robot_id, enable=True)
        self.conn.send_msg(msg)

    async def _delete_all_objects(self):
        # XXX marked this as private as apparently problematic to call
        # currently as it deletes light cubes too.
        msg = _clad_to_engine_iface.DeleteAllObjects(robotID=self.robot.robot_id)
        self.conn.send_msg(msg)
        await self.wait_for(_clad._MsgRobotDeletedAllObjects)
        # TODO: reset local object state

    async def delete_all_custom_objects(self):
        """Causes the robot to forget about all custom objects it currently knows about."""
        msg = _clad_to_engine_iface.DeleteAllCustomObjects(robotID=self.robot.robot_id)
        self.conn.send_msg(msg)
        # TODO: use a filter to wait only for a message for the active robot
        await self.wait_for(_clad._MsgRobotDeletedAllCustomObjects)
        # TODO: reset local object stte

    async def _define_custom_object(self, object_type, x_size_mm, y_size_mm, z_size_mm,
                                   marker_width_mm=25, marker_height_mm=25):
        '''Defines a cuboid of custom size and binds it to a specific custom object type.

        Warning: This function is currently experimental and has several known issues.
        1) There seems to be an off by 10x issue related to how the vision reports the object's
        size and position.
        2) The ID returned for these objects is not consistent.
        3) Poor performance and other issues have been seen in the App when using this.
        We plan to expand and improve upon it in a future release before making
        it fully public and documented.

        The engine will now detect the markers associated with this object and send an
        object_observed message when they are seen. The markers must be placed in the center
        of their respective sides.

        Args:
            object_type (:class:`cozmo.objects.CustomObjectTypes`): the object
                type you are binding this custom object to
            x_size_mm (float): size of the object (in millimeters) in the x axis.
            y_size_mm (float): size of the object (in millimeters) in the y axis.
            z_size_mm (float): size of the object (in millimeters) in the z axis.
            marker_width_mm (float): width of the printed marker (in millimeters).
            maker_height_mm (float): height of the printed marker (in millimeters).

        Returns:
            A :class:`cozmo.object.CustomObject` instance with the specified dimensions.
                This is not included in the world until it has been seen.

        Star Image:

        .. image:: ../images/star5.png

        Arrow Image:

        .. image:: ../images/arrow.png

        The markers must be placed in the same order as listed below:

        Custom_STAR5_Box:
            * Front - Star5
            * Back - Arrow

        Custom_STAR5_Cube:
            * All 6 faces - Star5

        Custom_ARROW_Box:
            * Front - Arrow
            * Back - Star5

        Custom_ARROW_Cube:
            * All 6 faces - Arrow
        '''
        # TODO make diagram for above docs!
        if not isinstance(object_type, objects._CustomObjectType):
            raise TypeError("Unsupported object_type, requires CustomObjectType")
        custom_object_base = self.custom_object_factory(object_type,
                                                        x_size_mm, y_size_mm, z_size_mm,
                                                        marker_width_mm, marker_height_mm,
                                                        self.conn, self, dispatch_parent=self)
        self.custom_objects[object_type.id] = custom_object_base
        msg = _clad_to_engine_iface.DefineCustomObject(objectType=object_type.id,
                                                       xSize_mm=x_size_mm, ySize_mm=y_size_mm, zSize_mm=z_size_mm,
                                                       markerWidth_mm=marker_width_mm, markerHeight_mm=marker_height_mm)
        self.conn.send_msg(msg)
        await self.wait_for(_clad._MsgDefinedCustomObject)
        return custom_object_base

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
            A :class:`cozmo.object.FixedCustomObject` instance with the specified dimensions and pose.
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

    def annotate_image(self, scale=None, fit_size=None):
        '''Adds any enabled annotations to the image.

        Optionally resizes the image prior to annotations being applied.  The
        aspect ratio of the resulting image always matches that of the raw image.

        Args:
            scale (float): If set then the base image will be scaled by the
                supplied multiplier.  Cannot be combined with fit_size
            fit_size (tuple of ints (width, height)):  If set, then scale the
                image to fit inside the supplied dimensions.  The original
                aspect ratio will be preserved.  Cannot be combined with scale.
        Returns:
            :class:`PIL.Image.Image`
        '''
        return self.image_annotator.annotate_image(self.raw_image, scale=scale, fit_size=fit_size)
