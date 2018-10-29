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

'''Object and Power Cube recognition.

Cozmo can recognize and track a number of different types of objects.

These objects may be visible (currently observed by the robot's camera)
and tappable (in the case of the Power Cubes that ship with the robot).

Power Cubes are known as a :class:`LightCube` by the SDK.  Each cube has
controllable lights, and sensors that can determine when its being moved
or tapped.

Objects can emit several events such as :class:`EvtObjectObserved` when
the robot sees (or continues to see) the object with its camera, or
:class:`EvtObjectTapped` if a power cube is tapped by a player.  You
can either observe the object's instance directly, or capture all such events
for all objects by observing them on :class:`cozmo.world.World` instead.

All observable objects have a marker attached to them, which allows Cozmo
to recognize the object and it's position and rotation("pose").  You can attach
markers to your own objects for Cozmo to recognize by printing them out from the
online documentation.  They will be detected as :class:`CustomObject` instances.
'''


# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['LightCube1Id', 'LightCube2Id', 'LightCube3Id', 'LightCubeIDs',
           'OBJECT_VISIBILITY_TIMEOUT',
           'EvtObjectAppeared',
           'EvtObjectConnectChanged', 'EvtObjectConnected',
           'EvtObjectDisappeared', 'EvtObjectLocated',
           'EvtObjectMoving', 'EvtObjectMovingStarted', 'EvtObjectMovingStopped',
           'EvtObjectObserved', 'EvtObjectTapped',
           'ObservableElement', 'ObservableObject', 'LightCube', 'Charger',
           'CustomObject', 'CustomObjectMarkers', 'CustomObjectTypes', 'FixedCustomObject']


import collections
import math
import time

from . import logger

from . import action
from . import event
from . import lights
from . import util

from ._clad import _clad_to_engine_iface, _clad_to_game_cozmo, _clad_to_engine_cozmo, _clad_to_game_anki


#: Length of time in seconds to go without receiving an observed event before
#: assuming that Cozmo can no longer see an object.
OBJECT_VISIBILITY_TIMEOUT = 0.4


class EvtObjectObserved(event.Event):
    '''Triggered whenever an object is visually identified by the robot.

    A stream of these events are produced while an object is visible to the robot.
    Each event has an updated image_box field.

    See EvtObjectAppeared if you only want to know when an object first
    becomes visible.
    '''
    obj = 'The object that was observed'
    updated = 'A set of field names that have changed'
    image_box = 'A comzo.util.ImageBox defining where the object is within Cozmo\'s camera view'
    pose = 'The cozmo.util.Pose defining the position and rotation of the object'


class EvtObjectAppeared(event.Event):
    '''Triggered whenever an object is first visually identified by a robot.

    This differs from EvtObjectObserved in that it's only triggered when
    an object initially becomes visible.  If it disappears for more than
    OBJECT_VISIBILITY_TIMEOUT seconds and then is seen again, a
    EvtObjectDisappeared will be dispatched, followed by another
    EvtObjectAppeared event.

    For continuous tracking information about a visible object, see
    EvtObjectObserved.
    '''
    obj = 'The object that was observed'
    updated = 'A set of field names that have changed'
    image_box = 'A comzo.util.ImageBox defining where the object is within Cozmo\'s camera view'
    pose = 'The cozmo.util.Pose defining the position and rotation of the object'


class EvtObjectConnected(event.Event):
    '''Triggered when the engine reports that an object is connected (i.e. exists).

    This will usually occur at the start of the program in response to the SDK
    sending RequestConnectedObjects to the engine.
    '''
    obj = 'The object that is connected'
    connected = 'True if the object connected, False if it disconnected'


class EvtObjectConnectChanged(event.Event):
    'Triggered when an active object has connected or disconnected from the robot.'
    obj = 'The object that connected or disconnected'
    connected = 'True if the object connected, False if it disconnected'


class EvtObjectLocated(event.Event):
    '''Triggered when the engine reports that an object is located (i.e. pose is known).

    This will usually occur at the start of the program in response to the SDK
    sending RequestLocatedObjectStates to the engine.
    '''
    obj = 'The object that is located'
    updated = 'A set of field names that have changed'
    pose = 'The cozmo.util.Pose defining the position and rotation of the object'


class EvtObjectDisappeared(event.Event):
    '''Triggered whenever an object that was previously being observed is no longer visible.'''
    obj = 'The object that is no longer being observed'

class EvtObjectMoving(event.Event):
    'Triggered when an active object is currently moving.'
    obj = 'The object that is currently moving'
    # :class:`~cozmo.util.Vector3`: The currently measured acceleration
    acceleration = 'The currently measured acceleration'
    move_duration = 'The current duration of time (in seconds) that the object has spent moving'

class EvtObjectMovingStarted(event.Event):
    'Triggered when an active object starts moving.'
    obj = 'The object that started moving'
    #: :class:`~cozmo.util.Vector3`: The currently measured acceleration
    acceleration = 'The currently measured acceleration'

class EvtObjectMovingStopped(event.Event):
    'Triggered when an active object stops moving.'
    obj = 'The object that stopped moving'
    move_duration = 'The duration of time (in seconds) that the object spent moving'

class EvtObjectTapped(event.Event):
    'Triggered when an active object is tapped.'
    obj = 'The object that was tapped'
    tap_count = 'Number of taps detected'
    tap_duration = 'The duration of the tap in ms'
    tap_intensity = 'The intensity of the tap'


class ObservableElement(event.Dispatcher):
    '''The base type for anything Cozmo can see.'''

    #: Length of time in seconds to go without receiving an observed event before
    #: assuming that Cozmo can no longer see an element. Can be overridden in sub
    #: classes.
    visibility_timeout = OBJECT_VISIBILITY_TIMEOUT

    def __init__(self, conn, world, robot, **kw):
        super().__init__(**kw)
        self._robot = robot
        self._pose = None
        self.conn = conn
        #: :class:`cozmo.world.World`: The robot's world in which this element is located.
        self.world = world

        #: float: The time the last event was received.
        #: ``None`` if no events have yet been received.
        self.last_event_time = None

        #: float: The time the element was last observed by the robot.
        #: ``None`` if the element has not yet been observed.
        self.last_observed_time = None

        #: int: The robot's timestamp of the last observed event.
        #: ``None`` if the element has not yet been observed.
        #: In milliseconds relative to robot epoch.
        self.last_observed_robot_timestamp = None

        #: :class:`~cozmo.util.ImageBox`: The ImageBox defining where the
        #: object was last visible within Cozmo's camera view.
        #: ``None`` if the element has not yet been observed.
        self.last_observed_image_box = None

        self._is_visible = False
        self._observed_timeout_handler = None

    def __repr__(self):
        extra = self._repr_values()
        if len(extra) > 0:
            extra = ' '+extra
        if self.pose:
            extra += ' pose=%s' % self.pose

        return '<%s%s is_visible=%s>' % (self.__class__.__name__,
                                         extra, self.is_visible)

    #### Private Methods ####

    def _repr_values(self):
        return ''

    def _update_field(self, changed, field_name, new_value):
        # Set only changed fields and update the passed in changed set
        current = getattr(self, field_name)
        if current != new_value:
            setattr(self, field_name, new_value)
            changed.add(field_name)

    def _reset_observed_timeout_handler(self):
        if self._observed_timeout_handler is not None:
            self._observed_timeout_handler.cancel()
        self._observed_timeout_handler = self._loop.call_later(
            self.visibility_timeout, self._observed_timeout)

    def _observed_timeout(self):
        # triggered when the element is no longer considered "visible"
        # ie. visibility_timeout seconds after the last observed event
        self._is_visible = False
        self._dispatch_disappeared_event()

    def _dispatch_observed_event(self, changed_fields, image_box):
        # Override in subclass if there is a specific event for that type
        pass

    def _dispatch_appeared_event(self, changed_fields, image_box):
        # Override in subclass if there is a specific event for that type
        pass

    def _dispatch_disappeared_event(self):
        # Override in subclass if there is a specific event for that type
        pass

    def _on_observed(self, image_box, timestamp, changed_fields):
        # Called from subclasses on their corresponding observed messages
        newly_visible = self._is_visible is False
        self._is_visible = True

        changed_fields |= {'last_observed_time', 'last_observed_robot_timestamp',
                           'last_event_time', 'last_observed_image_box'}

        now = time.time()
        self.last_observed_time = now
        self.last_observed_robot_timestamp = timestamp
        self.last_event_time = now
        self.last_observed_image_box = image_box
        self._reset_observed_timeout_handler()
        self._dispatch_observed_event(changed_fields, image_box)

        if newly_visible:
            self._dispatch_appeared_event(changed_fields, image_box)

    #### Properties ####

    @property
    def pose(self):
        ''':class:`cozmo.util.Pose`: The pose of the element in the world.

        Is ``None`` for elements that don't have pose information.
        '''
        return self._pose

    @property
    def time_since_last_seen(self):
        '''float: time since this element was last seen (math.inf if never)'''
        if self.last_observed_time is None:
            return math.inf
        return time.time() - self.last_observed_time

    @property
    def is_visible(self):
        '''bool: True if the element has been observed recently.

        "recently" is defined as :attr:`visibility_timeout` seconds.
        '''
        return self._is_visible


class ObservableObject(ObservableElement):
    '''The base type for objects in Cozmo's world.

    See parent class :class:`ObservableElement` for additional properties
    and methods.
    '''

    #: bool: True if this type of object can be physically picked up by Cozmo
    pickupable = False
    #: bool: True if this type of object can have objects physically placed on it by Cozmo
    place_objects_on_this = False

    def __init__(self, conn, world, object_id=None, **kw):
        super().__init__(conn, world, robot=None, **kw)
        self._object_id = object_id

    #### Private Methods ####

    def _repr_values(self):
        return 'object_id=%s' % self.object_id

    def _dispatch_observed_event(self, changed_fields, image_box):
        self.dispatch_event(EvtObjectObserved, obj=self,
                updated=changed_fields, image_box=image_box, pose=self._pose)

    def _dispatch_appeared_event(self, changed_fields, image_box):
        self.dispatch_event(EvtObjectAppeared, obj=self,
                updated=changed_fields, image_box=image_box, pose=self._pose)

    def _dispatch_disappeared_event(self):
        self.dispatch_event(EvtObjectDisappeared, obj=self)

    def _handle_connected_object_state(self, object_state):
        # triggered when engine sends a ConnectedObjectStates message
        # as a response to a RequestConnectedObjects message
        self._pose = util.Pose._create_default()
        self.is_connected = True
        self.dispatch_event(EvtObjectConnected, obj=self)

    def _handle_located_object_state(self, object_state):
        # triggered when engine sends a LocatedObjectStates message
        # as a response to a RequestLocatedObjectStates message
        if (self.last_observed_robot_timestamp and
            (self.last_observed_robot_timestamp > object_state.lastObservedTimestamp)):
            logger.warning("Ignoring old located object_state=%s obj=%s (last_observed_robot_timestamp=%s)",
                           object_state, self, self.last_observed_robot_timestamp)
            return

        changed_fields = {'last_observed_robot_timestamp', 'pose'}

        self.last_observed_robot_timestamp = object_state.lastObservedTimestamp

        self._pose = util.Pose._create_from_clad(object_state.pose)
        if object_state.poseState == _clad_to_game_anki.PoseState.Invalid:
            logger.error("Unexpected Invalid pose state received")
            self._pose.invalidate()
        elif object_state.poseState == _clad_to_game_anki.PoseState.Dirty:
            # Note Dirty currently means either moved (in which case it's really dirty)
            # or inaccurate (e.g. seen from too far away to give an accurate enough pose for localization)
            # TODO: split Dirty into 2 states, and allow SDK to report the distinction.
            self._pose._is_accurate = False

        self.dispatch_event(EvtObjectLocated,
                            obj=self,
                            updated=changed_fields,
                            pose=self._pose)

    #### Properties ####

    @property
    def object_id(self):
        '''int: The internal ID assigned to the object.

        This value can only be assigned once as it is static in the engine.
        '''
        return self._object_id

    @object_id.setter
    def object_id(self, value):
        if self._object_id is not None:
            # We cannot currently rely on Engine ensuring that object ID remains static
            # E.g. in the case of a cube disconnecting and reconnecting it's removed
            # and then re-added to blockworld which results in a new ID.
            logger.warning("Changing object_id for %s from %s to %s", self.__class__, self._object_id, value)
        else:
            logger.debug("Setting object_id for %s to %s", self.__class__, value)
        self._object_id = value

    @property
    def descriptive_name(self):
        '''str: A descriptive name for this ObservableObject instance.'''
        # Note: Sub-classes should override this to add any other relevant info
        # for that object type.
        return "%s id=%d" % (self.__class__.__name__, self.object_id)

    #### Private Event Handlers ####

    def _recv_msg_robot_observed_object(self, evt, *, msg):

        changed_fields = {'pose'}
        self._pose = util.Pose._create_from_clad(msg.pose)

        image_box = util.ImageBox._create_from_clad_rect(msg.img_rect)
        self._on_observed(image_box, msg.timestamp, changed_fields)

    #### Public Event Handlers ####

    #### Event Wrappers ####

    #### Commands ####


#: LightCube1Id's markers look a bit like a paperclip
LightCube1Id = _clad_to_game_cozmo.ObjectType.Block_LIGHTCUBE1
#: LightCube2Id's markers look a bit like a lamp (or a heart)
LightCube2Id = _clad_to_game_cozmo.ObjectType.Block_LIGHTCUBE2
#: LightCube3Id's markers look a bit like the letters 'ab' over 'T'
LightCube3Id = _clad_to_game_cozmo.ObjectType.Block_LIGHTCUBE3

#: An ordered list of the 3 light cube IDs for convenience
LightCubeIDs = [LightCube1Id, LightCube2Id, LightCube3Id]


class LightCube(ObservableObject):
    '''A light cube object has four LEDs that Cozmo can actively manipulate and communicate with.

    See parent class :class:`ObservableObject` for additional properties
    and methods.
    '''
    #TODO investigate why the top marker orientation of a cube is a bit strange

    #: Voltage where a cube's battery can be considered empty
    EMPTY_VOLTAGE = 1.0
    #: Voltage where a cube's battery can be considered full
    FULL_VOLTAGE = 1.5

    pickupable = True
    place_objects_on_this = True

    def __init__(self, cube_id, *a, **kw):
        super().__init__(*a, **kw)

        #: float: The time the object was last tapped
        #: ``None`` if the cube wasn't tapped yet.
        self.last_tapped_time = None

        #: int: The robot's timestamp of the last tapped event.
        #: ``None`` if the cube wasn't tapped yet.
        #: In milliseconds relative to robot epoch.
        self.last_tapped_robot_timestamp = None

        #: float: The time the object was last moved
        #: ``None`` if the cube wasn't moved yet.
        self.last_moved_time = None

        #: float: The time the object started moving when last moved
        self.last_moved_start_time = None

        #: int: The robot's timestamp of the last move event.
        #: ``None`` if the cube wasn't moved yet.
        #: In milliseconds relative to robot epoch.
        self.last_moved_robot_timestamp = None

        #: int: The robot's timestamp of when the object started moving when last moved
        #: ``None`` if the cube wasn't moved yet.
        #: In milliseconds relative to robot epoch.
        self.last_moved_start_robot_timestamp = None

        #: float: Battery voltage.
        #: ``None`` if no voltage reading has been received yet
        self.battery_voltage = None

        #: bool: True if the cube's accelerometer indicates that the cube is moving.
        self.is_moving = False

        #: bool: True if the cube is currently connected to the robot via radio.
        self.is_connected = False

        self._cube_id = cube_id

    def _repr_values(self):
        super_values = super()._repr_values()
        if len(super_values) > 0:
            super_values += ' '
        return ('{super_values}'
                'battery={self.battery_str:s}'.format(self=self, super_values=super_values))

    #### Private Methods ####

    def _set_light(self, msg, idx, light):
        if not isinstance(light, lights.Light):
            raise TypeError("Expected a lights.Light")
        msg.onColor[idx] = light.on_color.int_color
        msg.offColor[idx] = light.off_color.int_color
        msg.onPeriod_ms[idx] = light.on_period_ms
        msg.offPeriod_ms[idx] = light.off_period_ms
        msg.transitionOnPeriod_ms[idx] = light.transition_on_period_ms
        msg.transitionOffPeriod_ms[idx] = light.transition_off_period_ms


    #### Event Wrappers ####

    async def wait_for_tap(self, timeout=None):
        '''Wait for the object to receive a tap event.

        Args:
            timeout (float): Maximum time to wait for a tap, in seconds.  None for indefinite
        Returns:
            A :class:`EvtObjectTapped` object if a tap was received.
        '''
        return await self.wait_for(EvtObjectTapped, timeout=timeout)


    #### Properties ####

    @property
    def battery_percentage(self):
        """float: Battery level as a percentage."""
        if self.battery_voltage is None:
            # not received a voltage measurement yet
            return None
        elif self.battery_voltage >= self.FULL_VOLTAGE:
            return 100.0
        elif self.battery_voltage <= self.EMPTY_VOLTAGE:
            return 0.0
        else:
            return 100.0 * ((self.battery_voltage - self.EMPTY_VOLTAGE) /
                            (self.FULL_VOLTAGE - self.EMPTY_VOLTAGE))

    @property
    def battery_str(self):
        """str: String representation of the battery level."""
        if self.battery_voltage is None:
            return "Unknown"
        else:
            return ('{self.battery_percentage:.0f}%'.format(self=self))

    @property
    def cube_id(self):
        """int: The Light Cube ID.

        This will be one of :attr:`~cozmo.objects.LightCube1Id`,
        :attr:`~cozmo.objects.LightCube2Id` and :attr:`~cozmo.objects.LightCube3Id`.
        Note: the cube_id is not the same thing as the object_id.
        """
        return self._cube_id

    #### Private Event Handlers ####
    def _recv_msg_object_tapped(self, evt, *, msg):
        now = time.time()
        self.last_event_time = now
        self.last_tapped_time = now
        self.last_tapped_robot_timestamp = msg.timestamp
        tap_intensity = msg.tapPos - msg.tapNeg
        self.dispatch_event(EvtObjectTapped, obj=self,
            tap_count=msg.numTaps, tap_duration=msg.tapTime, tap_intensity=tap_intensity)

    def _recv_msg_object_moved(self, evt, *, msg):
        now = time.time()
        started_moving = not self.is_moving
        self.is_moving = True
        self.last_event_time = now
        self.last_moved_time = now
        self.last_moved_robot_timestamp = msg.timestamp

        self.pose.invalidate()

        acceleration = util.Vector3(msg.accel.x, msg.accel.y, msg.accel.z)

        if started_moving:
            self.last_moved_start_time = now
            self.last_moved_start_robot_timestamp = msg.timestamp
            self.dispatch_event(EvtObjectMovingStarted, obj=self,
                                acceleration=acceleration)
        else:
            move_duration = now - self.last_moved_start_time
            self.dispatch_event(EvtObjectMoving, obj=self,
                                acceleration=acceleration,
                                move_duration=move_duration)

    def _recv_msg_object_stopped_moving(self, evt, *, msg):
        now = time.time()
        if self.is_moving:
            self.is_moving = False
            move_duration = now - self.last_moved_start_time
        else:
            # This happens for very short movements that are immediately
            # considered stopped (no acceleration info is present)
            move_duration = 0.0
        self.dispatch_event(EvtObjectMovingStopped, obj=self,
                            move_duration=move_duration)

    def _recv_msg_object_power_level(self, evt, *, msg):
        self.battery_voltage = msg.batteryLevel * 0.01

    def _recv_msg_object_connection_state(self, evt, *, msg):
        if self.is_connected != msg.connected:
            if msg.connected:
                logger.info("Object connected: %s", self)
            else:
                logger.info("Object disconnected: %s", self)
            self.is_connected = msg.connected
            self.dispatch_event(EvtObjectConnectChanged, obj=self,
                                connected=self.is_connected)

    @property
    def descriptive_name(self):
        '''str: A descriptive name for this LightCube instance.'''
        # Specialization of ObservableObject's method to include the cube ID.
        return "%s %s id=%d" % (self.__class__.__name__, self._cube_id, self.object_id)

    #### Public Event Handlers ####

    def recv_evt_object_tapped(self, evt, **kw):
        pass

    #### Commands ####

    # TODO: make this explicit as to which light goes to which corner.
    def set_light_corners(self, light1, light2, light3, light4):
        """Set the light for each corner"""
        msg = _clad_to_engine_iface.SetAllActiveObjectLEDs(objectID=self.object_id)
        for i, light in enumerate( (light1, light2, light3, light4) ):
            if light is not None:
                lights._set_light(msg, i, light)

        self.conn.send_msg(msg)

    def set_lights(self, light):
        '''Set all lights on the cube

        Args:
            light (:class:`cozmo.lights.Light`): The settings for the lights.
        '''
        msg = _clad_to_engine_iface.SetAllActiveObjectLEDs(
                objectID=self.object_id)
        for i in range(4):
            lights._set_light(msg, i, light)

        self.conn.send_msg(msg)

    def set_lights_off(self):
        '''Turn off all the lights on the cube.'''
        self.set_lights(lights.off_light)


class Charger(ObservableObject):
    '''Cozmo's charger object, which the robot can observe and drive toward.

    See parent class :class:`ObservableObject` for additional properties
    and methods.
    '''

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)


class CustomObject(ObservableObject):
    '''An object defined by the SDK. It is bound to a specific objectType e.g ``CustomType00``.

    This defined object is given a size in the x,y and z axis. The dimensions
    of the markers on the object are also defined. We get an
    :class:`cozmo.objects.EvtObjectObserved` message when the robot sees these
    markers.

    See parent class :class:`ObservableObject` for additional properties
    and methods.
    
    These objects are created automatically by the engine when Cozmo observes
    an object with custom markers. For Cozmo to see one of these you must first
    define an object with custom markers, via one of the following methods:
    :meth:`~cozmo.world.World.define_custom_box`.
    :meth:`~cozmo.world.World.define_custom_cube`, or
    :meth:`~cozmo.world.World.define_custom_wall`
    '''

    def __init__(self, conn, world, object_type,
                 x_size_mm, y_size_mm, z_size_mm,
                 marker_width_mm, marker_height_mm, is_unique, **kw):
        super().__init__(conn, world, **kw)

        self.object_type = object_type
        self._x_size_mm = x_size_mm
        self._y_size_mm = y_size_mm
        self._z_size_mm = z_size_mm
        self._marker_width_mm = marker_width_mm
        self._marker_height_mm = marker_height_mm
        self._is_unique = is_unique

    def _repr_values(self):
        return ('object_type={self.object_type} '
                'x_size_mm={self.x_size_mm:.1f} '
                'y_size_mm={self.y_size_mm:.1f} '
                'z_size_mm={self.z_size_mm:.1f} '
                'is_unique={self.is_unique}'.format(self=self))

    #### Private Methods ####

    #### Event Wrappers ####
    #### Properties ####
    @property
    def x_size_mm(self):
        '''float: Size of this object in its X axis, in millimeters.'''
        return self._x_size_mm

    @property
    def y_size_mm(self):
        '''float: Size of this object in its Y axis, in millimeters.'''
        return self._y_size_mm

    @property
    def z_size_mm(self):
        '''float: Size of this object in its Z axis, in millimeters.'''
        return self._z_size_mm

    @property
    def marker_width_mm(self):
        '''float: Width in millimeters of the marker on this object.'''
        return self._marker_width_mm

    @property
    def marker_height_mm(self):
        '''float: Height in millimeters of the marker on this object.'''
        return self._marker_height_mm

    @property
    def is_unique(self):
        '''bool: True if there should only be one of this object type in the world.'''
        return self._is_unique

    @property
    def descriptive_name(self):
        '''str: A descriptive name for this CustomObject instance.'''
        # Specialization of ObservableObject's method to include the object type.
        return "%s id=%d" % (self.object_type.name, self.object_id)

    #### Private Event Handlers ####

    #### Public Event Handlers ####

    #### Commands ####


class _CustomObjectType(collections.namedtuple('_CustomObjectType', 'name id')):
    # Tuple mapping between CLAD ActionResult name and ID
    # All instances will be members of ActionResults

    # Keep _ActionResult as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'CustomObjectTypes.%s' % self.name


class CustomObjectTypes:
    '''Defines all available custom object types.

    For use with world.define_custom methods such as
    :meth:`cozmo.world.World.define_custom_box`,
    :meth:`cozmo.world.World.define_custom_cube`, and
    :meth:`cozmo.world.World.define_custom_wall`
    '''

    #: CustomType00 - the first custom object type
    CustomType00 = _CustomObjectType("CustomType00", _clad_to_engine_cozmo.ObjectType.CustomType00)

    #:
    CustomType01 = _CustomObjectType("CustomType01", _clad_to_engine_cozmo.ObjectType.CustomType01)

    #:
    CustomType02 = _CustomObjectType("CustomType02", _clad_to_engine_cozmo.ObjectType.CustomType02)

    #:
    CustomType03 = _CustomObjectType("CustomType03", _clad_to_engine_cozmo.ObjectType.CustomType03)

    #:
    CustomType04 = _CustomObjectType("CustomType04", _clad_to_engine_cozmo.ObjectType.CustomType04)

    #:
    CustomType05 = _CustomObjectType("CustomType05", _clad_to_engine_cozmo.ObjectType.CustomType05)

    #:
    CustomType06 = _CustomObjectType("CustomType06", _clad_to_engine_cozmo.ObjectType.CustomType06)

    #:
    CustomType07 = _CustomObjectType("CustomType07", _clad_to_engine_cozmo.ObjectType.CustomType07)

    #:
    CustomType08 = _CustomObjectType("CustomType08", _clad_to_engine_cozmo.ObjectType.CustomType08)

    #:
    CustomType09 = _CustomObjectType("CustomType09", _clad_to_engine_cozmo.ObjectType.CustomType09)

    #:
    CustomType10 = _CustomObjectType("CustomType10", _clad_to_engine_cozmo.ObjectType.CustomType10)

    #:
    CustomType11 = _CustomObjectType("CustomType11", _clad_to_engine_cozmo.ObjectType.CustomType11)

    #:
    CustomType12 = _CustomObjectType("CustomType12", _clad_to_engine_cozmo.ObjectType.CustomType12)

    #:
    CustomType13 = _CustomObjectType("CustomType13", _clad_to_engine_cozmo.ObjectType.CustomType13)

    #:
    CustomType14 = _CustomObjectType("CustomType14", _clad_to_engine_cozmo.ObjectType.CustomType14)

    #:
    CustomType15 = _CustomObjectType("CustomType15", _clad_to_engine_cozmo.ObjectType.CustomType15)

    #:
    CustomType16 = _CustomObjectType("CustomType16", _clad_to_engine_cozmo.ObjectType.CustomType16)

    #:
    CustomType17 = _CustomObjectType("CustomType17", _clad_to_engine_cozmo.ObjectType.CustomType17)

    #:
    CustomType18 = _CustomObjectType("CustomType18", _clad_to_engine_cozmo.ObjectType.CustomType18)

    #: CustomType19 - the last custom object type
    CustomType19 = _CustomObjectType("CustomType19", _clad_to_engine_cozmo.ObjectType.CustomType19)


_CustomObjectMarker = collections.namedtuple('_CustomObjectMarker', 'name id')

class CustomObjectMarkers:
    '''Defines all available custom object markers.

    For use with world.define_custom methods such as
    :meth:`cozmo.world.World.define_custom_box`,
    :meth:`cozmo.world.World.define_custom_cube`, and
    :meth:`cozmo.world.World.define_custom_wall`
    '''

    #: .. image:: ../images/custom_markers/SDK_2Circles.png
    Circles2 = _CustomObjectMarker("Circles2", _clad_to_engine_cozmo.CustomObjectMarker.Circles2)

    #: .. image:: ../images/custom_markers/SDK_3Circles.png
    Circles3 = _CustomObjectMarker("Circles3", _clad_to_engine_cozmo.CustomObjectMarker.Circles3)

    #: .. image:: ../images/custom_markers/SDK_4Circles.png
    Circles4 = _CustomObjectMarker("Circles4", _clad_to_engine_cozmo.CustomObjectMarker.Circles4)

    #: .. image:: ../images/custom_markers/SDK_5Circles.png
    Circles5 = _CustomObjectMarker("Circles5", _clad_to_engine_cozmo.CustomObjectMarker.Circles5)

    #: .. image:: ../images/custom_markers/SDK_2Diamonds.png
    Diamonds2 = _CustomObjectMarker("Diamonds2", _clad_to_engine_cozmo.CustomObjectMarker.Diamonds2)

    #: .. image:: ../images/custom_markers/SDK_3Diamonds.png
    Diamonds3 = _CustomObjectMarker("Diamonds3", _clad_to_engine_cozmo.CustomObjectMarker.Diamonds3)

    #: .. image:: ../images/custom_markers/SDK_4Diamonds.png
    Diamonds4 = _CustomObjectMarker("Diamonds4", _clad_to_engine_cozmo.CustomObjectMarker.Diamonds4)

    #: .. image:: ../images/custom_markers/SDK_5Diamonds.png
    Diamonds5 = _CustomObjectMarker("Diamonds5", _clad_to_engine_cozmo.CustomObjectMarker.Diamonds5)

    #: .. image:: ../images/custom_markers/SDK_2Hexagons.png
    Hexagons2 = _CustomObjectMarker("Hexagons2", _clad_to_engine_cozmo.CustomObjectMarker.Hexagons2)

    #: .. image:: ../images/custom_markers/SDK_3Hexagons.png
    Hexagons3 = _CustomObjectMarker("Hexagons3", _clad_to_engine_cozmo.CustomObjectMarker.Hexagons3)

    #: .. image:: ../images/custom_markers/SDK_4Hexagons.png
    Hexagons4 = _CustomObjectMarker("Hexagons4", _clad_to_engine_cozmo.CustomObjectMarker.Hexagons4)

    #: .. image:: ../images/custom_markers/SDK_5Hexagons.png
    Hexagons5 = _CustomObjectMarker("Hexagons5", _clad_to_engine_cozmo.CustomObjectMarker.Hexagons5)

    #: .. image:: ../images/custom_markers/SDK_2Triangles.png
    Triangles2 = _CustomObjectMarker("Triangles2", _clad_to_engine_cozmo.CustomObjectMarker.Triangles2)

    #: .. image:: ../images/custom_markers/SDK_3Triangles.png
    Triangles3 = _CustomObjectMarker("Triangles3", _clad_to_engine_cozmo.CustomObjectMarker.Triangles3)

    #: .. image:: ../images/custom_markers/SDK_4Triangles.png
    Triangles4 = _CustomObjectMarker("Triangles4", _clad_to_engine_cozmo.CustomObjectMarker.Triangles4)

    #: .. image:: ../images/custom_markers/SDK_5Triangles.png
    Triangles5 = _CustomObjectMarker("Triangles5", _clad_to_engine_cozmo.CustomObjectMarker.Triangles5)


class FixedCustomObject():
    '''A fixed object defined by the SDK. It is given a pose and x,y,z sizes.

    This object cannot be observed by the robot so its pose never changes.
    The position is static in Cozmo's world view; once instantiated, these
    objects never move. This could be used to make Cozmo aware of objects and
    know to plot a path around them even when they don't have any markers.
    
    To create these use :meth:`~cozmo.world.World.create_custom_fixed_object`
    '''

    is_visible = False

    def __init__(self, pose, x_size_mm, y_size_mm, z_size_mm, object_id, *a, **kw):
        super().__init__(*a, **kw)
        self._pose = pose
        self._object_id = object_id
        self._x_size_mm = x_size_mm
        self._y_size_mm = y_size_mm
        self._z_size_mm = z_size_mm

    def __repr__(self):
        return ('<%s pose=%s object_id=%d x_size_mm=%.1f y_size_mm=%.1f z_size_mm=%.1f=>' %
                                        (self.__class__.__name__, self.pose, self.object_id,
                                         self.x_size_mm, self.y_size_mm, self.z_size_mm))

    #### Private Methods ####
    #### Event Wrappers ####
    #### Properties ####
    @property
    def object_id(self):
        '''int: The internal ID assigned to the object.

        This value can only be assigned once as it is static in the engine.
        '''
        return self._object_id

    @object_id.setter
    def object_id(self, value):
        if self._object_id is not None:
            raise ValueError("Cannot change object ID once set (from %s to %s)" % (self._object_id, value))
        logger.debug("Updated object_id for %s from %s to %s", self.__class__, self._object_id, value)
        self._object_id = value

    @property
    def pose(self):
        ''':class:`cozmo.util.Pose`: The pose of the object in the world.'''
        return self._pose

    @property
    def x_size_mm(self):
        '''float: The length of the object in its X axis, in millimeters.'''
        return self._x_size_mm

    @property
    def y_size_mm(self):
        '''float: The length of the object in its Y axis, in millimeters.'''
        return self._y_size_mm

    @property
    def z_size_mm(self):
        '''float: The length of the object in its Z axis, in millimeters.'''
        return self._z_size_mm


    #### Private Event Handlers ####
    #### Public Event Handlers ####
    #### Commands ####
