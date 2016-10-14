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

'''Classes and functions relating to an individual Cozmo robot.

The :meth:`cozmo.conn.CozmoConnection.wait_for_robot` method returns an
instance of :class:`Robot` which controls a single Cozmo robot.

The :class:`Robot` class has methods and properties to determine its current
state, control its low-level motors, play animations and start behaviors as
well as performing high-level actions such as detecting faces and picking up
objects.

Each :class:`Robot` has a :attr:`Robot.world` attribute which represents an
instance of a :class:`cozmo.world.World`.  This tracks the state of the world
that Cozmo knows about:  The objects and faces it's currently observing,
the camera images it's receiving, etc.  You can monitor the world instance for
various events that occur, or monitor individual objects directly:  The
world instance receives all events that the robot triggers, and nearly all SDK
objects inherit from :class:`cozmo.event.Dispatcher` and therefore inherit
methods such as :meth:`~cozmo.event.Dispatcher.wait_for` and
:meth:`~cozmo.event.Dispatcher.add_event_handler`.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['MAX_HEAD_ANGLE', 'MIN_HEAD_ANGLE', 'MIN_LIFT_HEIGHT_MM', 'MAX_LIFT_HEIGHT_MM',
           'EvtRobotReady',
           'GoToPose', 'DriveOffChargerContacts', 'DriveStraight', 'PickupObject',
           'PlaceOnObject', 'PlaceObjectOnGroundHere', 'SayText', 'SetHeadAngle',
           'SetLiftHeight', 'TurnInPlace', 'TurnTowardsFace',
           'Robot']


import asyncio

from . import logger, logger_protocol
from . import action
from . import anim
from . import behavior
from . import camera
from . import conn
from . import event
from . import lights
from . import objects
from . import util
from . import world

from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo, _clad_to_game_cozmo


#### Events

class EvtRobotReady(event.Event):
    '''Generated when the robot has been initialized and is ready for commands'''
    robot = "Robot object representing the robot to command"


#### Constants


#: The minimum angle the robot's head can be set to
MIN_HEAD_ANGLE = util.degrees(-25)

#: The maximum angle the robot's head can be set to
MAX_HEAD_ANGLE = util.degrees(44.5)

#: The lowest height-above-ground that lift can be moved to
MIN_LIFT_HEIGHT_MM = 32.0

#: The largest height-above-ground that lift can be moved to
MAX_LIFT_HEIGHT_MM = 92.0


#### Actions

class GoToPose(action.Action):
    '''Represents the go to pose action in progress.

    Returned by :meth:`~cozmo.robot.Robot.go_to_pose`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.DRIVE_TO_POSE

    def __init__(self, pose, **kw):
        super().__init__(**kw)
        self.pose = pose

    def _repr_values(self):
        return "pose=%s" % (self.pose)

    def _encode(self):
        return _clad_to_engine_iface.GotoPose(x_mm=self.pose.position.x,
                                              y_mm=self.pose.position.y,
                                              rad=self.pose.rotation.angle_z.radians)


class DriveOffChargerContacts(action.Action):
    '''Represents the drive off charger contacts action in progress.

    Returned by :meth:`~cozmo.robot.Robot.drive_off_charger_contacts`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.DRIVE_OFF_CHARGER_CONTACTS

    def __init__(self, **kw):
        super().__init__(**kw)

    def _repr_values(self):
        return ""

    def _encode(self):
        return _clad_to_engine_iface.DriveOffChargerContacts()


class DriveStraight(action.Action):
    '''Represents the "drive straight" action in progress.

    Returned by :meth:`~cozmo.robot.Robot.drive_straight`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.DRIVE_STRAIGHT

    def __init__(self, distance, speed, should_play_anim, **kw):
        super().__init__(**kw)
        #: :class:`cozmo.util.Distance`: The distance to drive
        self.distance = distance
        #: :class:`cozmo.util.Speed`: The speed to drive at
        self.speed = speed
        #: bool: Whether to play an animation whilst driving
        self.should_play_anim = should_play_anim

    def _repr_values(self):
        return "distance=%s speed=%s should_play_anim=%s" % (self.distance, self.speed, self.should_play_anim)

    def _encode(self):
        return _clad_to_engine_iface.DriveStraight(speed_mmps=self.speed.speed_mmps,
                                                   dist_mm=self.distance.distance_mm,
                                                   shouldPlayAnimation=self.should_play_anim)


class PickupObject(action.Action):
    '''Represents the pickup object action in progress.

    Returned by :meth:`~cozmo.robot.Robot.pickup_object`
    '''

    def __init__(self, obj, use_pre_dock_pose=True, **kw):
        super().__init__(**kw)
        #: The object (e.g. an instance of :class:`cozmo.objects.LightCube`) that was picked up
        self.obj = obj
        #: A bool that is true when Cozmo needs to go to a pose before attempting to navigate to the object
        self.use_pre_dock_pose = use_pre_dock_pose

    def _repr_values(self):
        return "object=%s" % (self.obj,)

    def _encode(self):
        return _clad_to_engine_iface.PickupObject(objectID=self.obj.object_id,
                                                  usePreDockPose=self.use_pre_dock_pose)


class PlaceOnObject(action.Action):
    '''Tracks the state of the "place on object" action.

    return by :meth:`~cozmo.robot.Robot.place_on_object`
    '''

    def __init__(self, obj, use_pre_dock_pose=True, **kw):
        super().__init__(**kw)
        #: The object (e.g. an instance of :class:`cozmo.objects.LightCube`) that the held object will be placed on
        self.obj = obj
        #: A bool that is true when Cozmo needs to go to a pose before attempting to navigate to the object
        self.use_pre_dock_pose = use_pre_dock_pose

    def _repr_values(self):
        return "object=%s use_pre_dock_pose=%s" % (self.obj, self.use_pre_dock_pose)

    def _encode(self):
        return _clad_to_engine_iface.PlaceOnObject(objectID=self.obj.object_id,
                                                   usePreDockPose=self.use_pre_dock_pose)


class PlaceObjectOnGroundHere(action.Action):
    '''Tracks the state of the "place object on ground here" action.

    Returned by :meth:`~cozmo.robot.Robot.place_object_on_ground_here`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.PLACE_OBJECT_LOW

    def __init__(self, obj, **kw):
        super().__init__(**kw)
        #: The object (e.g. an instance of :class:`cozmo.objects.LightCube`) that is being put down
        self.obj = obj

    def _repr_values(self):
        return "object=%s" % (self.obj,)

    def _encode(self):
        return _clad_to_engine_iface.PlaceObjectOnGroundHere()


class SayText(action.Action):
    '''Tracks the progress of a say text robot action.

    Returned by :meth:`~cozmo.robot.Robot.say_text`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.SAY_TEXT

    def __init__(self, text, play_excited_animation, use_cozmo_voice, duration_scalar, voice_pitch, **kw):
        super().__init__(**kw)
        self.text = text

        # Note: play_event must be an AnimationTrigger that supports text-to-speech being generated

        if play_excited_animation:
            self.play_event = _clad_to_engine_cozmo.AnimationTrigger.OnSawNewNamedFace
        else:
            # TODO: Switch to use AnimationTrigger.SdkTextToSpeech when that works correctly
            self.play_event = _clad_to_engine_cozmo.AnimationTrigger.Count

        if use_cozmo_voice:
            self.say_style = _clad_to_engine_cozmo.SayTextVoiceStyle.CozmoProcessing
        else:
            # default male human voice
            self.say_style = _clad_to_engine_cozmo.SayTextVoiceStyle.UnProcessed

        self.duration_scalar = duration_scalar
        self.voice_pitch = voice_pitch

    def _repr_values(self):
        return "text='%s' style=%s event=%s duration=%s pitch=%s" %\
               (self.text, self.say_style, self.play_event, self.duration_scalar, self.voice_pitch)

    def _encode(self):
        return _clad_to_engine_iface.SayText(text=self.text,
                                             playEvent=self.play_event,
                                             voiceStyle=self.say_style,
                                             durationScalar=self.duration_scalar,
                                             voicePitch=self.voice_pitch)


class SetHeadAngle(action.Action):
    '''Represents the Set Head Angle action in progress.
       Returned by :meth:`~cozmo.robot.Robot.set_head_angle`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.MOVE_HEAD_TO_ANGLE

    def __init__(self, angle, max_speed, accel, duration, **kw):
        super().__init__(**kw)

        if angle < MIN_HEAD_ANGLE:
            logger.info("Clamping head angle from %s to min %s" % (angle, MIN_HEAD_ANGLE))
            self.angle = MIN_HEAD_ANGLE
        elif angle > MAX_HEAD_ANGLE:
            logger.info("Clamping head angle from %s to max %s" % (angle, MAX_HEAD_ANGLE))
            self.angle = MAX_HEAD_ANGLE
        else:
            self.angle = angle

        #: float: Maximum speed of Cozmo's head in radians per second
        self.max_speed = max_speed

        #: float: Acceleration of Cozmo's head in radians per second squared
        self.accel = accel

        #: float: Time for Cozmo's head to turn in seconds
        self.duration = duration

    def _repr_values(self):
        return "angle=%s max_speed=%s accel=%s duration=%s" %\
               (self.angle, self.max_speed, self.accel, self.duration)

    def _encode(self):
        return _clad_to_engine_iface.SetHeadAngle(angle_rad=self.angle.radians,
                                                  max_speed_rad_per_sec=self.max_speed,
                                                  accel_rad_per_sec2=self.accel,
                                                  duration_sec=self.duration)


class SetLiftHeight(action.Action):
    '''Represents the Set Lift Height action in progress.
       Returned by :meth:`~cozmo.robot.Robot.set_lift_height`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.MOVE_LIFT_TO_HEIGHT

    def __init__(self, height, max_speed, accel, duration, **kw):
        super().__init__(**kw)

        if height < 0.0:
            logger.warn("lift height %s too small, should be in 0..1 range - clamping" % height)
            self.lift_height_mm = MIN_LIFT_HEIGHT_MM
        elif height > 1.0:
            logger.warn("lift height %s too large, should be in 0..1 range - clamping" % height)
            self.lift_height_mm = MAX_LIFT_HEIGHT_MM
        else:
            self.lift_height_mm = MIN_LIFT_HEIGHT_MM + (height * (MAX_LIFT_HEIGHT_MM - MIN_LIFT_HEIGHT_MM))

        #: float: Maximum speed of Cozmo's head in radians per second
        self.max_speed = max_speed

        #: float: Acceleration of Cozmo's head in radians per second squared
        self.accel = accel

        #: float: Time for Cozmo's head to turn in seconds
        self.duration = duration

    def _repr_values(self):
        return "height=%s max_speed=%s accel=%s duration=%s" %\
               (self.lift_height_mm, self.max_speed, self.accel, self.duration)

    def _encode(self):
        return _clad_to_engine_iface.SetLiftHeight(height_mm=self.lift_height_mm,
                                                   max_speed_rad_per_sec=self.max_speed,
                                                   accel_rad_per_sec2=self.accel,
                                                   duration_sec=self.duration)


class TurnInPlace(action.Action):
    '''Tracks the progress of a turn in place robot action.

    Returned by :meth:`~cozmo.robot.Robot.turn_in_place`
    '''

    def __init__(self, angle, **kw):
        super().__init__(**kw)
        # :class:`cozmo.util.Angle`: The angle to turn
        self.angle = angle

    def _repr_values(self):
        return "angle=%s" % (self.angle,)

    def _encode(self):
        return _clad_to_engine_iface.TurnInPlace(
            angle_rad = self.angle.radians,
            isAbsolute = 0)


class TurnTowardsFace(action.Action):
    '''Tracks the progress of a turn towards face robot action.

    Returned by :meth:`~cozmo.robot.Robot.turn_towards_face`
    '''

    def __init__(self, face, **kw):
        super().__init__(**kw)
        #: :class:`~cozmo.faces.Face`: The face to turn towards
        self.face = face

    def _repr_values(self):
        return "face=%s" % (self.face)

    def _encode(self):
        return _clad_to_engine_iface.TurnTowardsFace(
            faceID=self.face.face_id)


class Robot(event.Dispatcher):
    """The interface to a Cozmo robot.

    A robot has access to:

    * A :class:`~cozmo.world.World` object (:attr:`cozmo.robot.Robot.world`),
        which tracks the state of the world the robot knows about

    * A :class:`~cozmo.camera.Camera` object (:attr:`cozmo.robot.Robot.camera`),
        which provides access to Cozmo's camera

    * An Animations object, controlling the playing of animations on the robot

    * A Behaviors object, starting and ending robot behaviors such as looking around

    Robots are instantiated by the :class:`~cozmo.conn.CozmoConnection` object
    and emit a :class:`EvtRobotReady` when it has been configured and is
    ready to be commanded.
    """

    # action factories
    _action_dispatcher_factory = action._ActionDispatcher

    #: callable: The factory function that returns a
    #: class:`TurnInPlace` class or subclass instance.
    turn_in_place_factory = TurnInPlace

    #: callable: The factory function that returns a
    #: class:`TurnTowardsFace` class or subclass instance.
    turn_towards_face_factory = TurnTowardsFace

    #: callable: The factory function that returns a
    #: class:`PickupObject` class or subclass instance.
    pickup_object_factory = PickupObject

    #: callable: The factory function that returns a
    #: class:`PlaceOnObject` class or subclass instance.
    place_on_object_factory = PlaceOnObject

    #: callable: The factory function that returns a
    #: class:`GoToPose` class or subclass instance.
    go_to_pose_factory = GoToPose

    #: callable: The factory function that returns a
    #: class:`PlaceObjectOnGroundHere` class or subclass instance.
    place_object_on_ground_here_factory = PlaceObjectOnGroundHere

    #: callable: The factory function that returns a
    #: class:`SayText` class or subclass instance.
    say_text_factory = SayText

    #: callable: The factory function that returns a
    #: class:`SetHeadAngle` class or subclass instance.
    set_head_angle_factory = SetHeadAngle

    #: callable: The factory function that returns a
    #: class:`SetLiftHeight` class or subclass instance.
    set_lift_height_factory = SetLiftHeight

    #: callable: The factory function that returns a
    #: class:`DriveOffChargerContacts` class or subclass instance.
    drive_off_charger_contacts_factory = DriveOffChargerContacts

    #: callable: The factory function that returns a
    #: class:`DriveStraight` class or subclass instance.
    drive_straight_factory = DriveStraight

    # other factories

    #: callable: The factory function that returns a
    #: class:`cozmo.anim.Animation` class or subclass instance.
    animation_factory = anim.Animation

    #: callable: The factory function that returns a
    #: class:`cozmo.anim.AnimationTrigger` class or subclass instance.
    animation_trigger_factory = anim.AnimationTrigger

    #: callable: The factory function that returns a
    #: class:`cozmo.behavior.Behavior` class or subclass instance.
    behavior_factory = behavior.Behavior

    #: callable: The factory function that returns a
    #: class:`cozmo.camera.Camera` class or subclass instance.
    camera_factory = camera.Camera

    #: callable: The factory function that returns a
    #: class:`cozmo.world.World` class or subclass instance.
    world_factory = world.World

    # other attributes

    #: bool: Set to True if the robot should drive off the charger as soon
    # as the SDK connects to the engine.  Defaults to True.
    drive_off_charger_on_connect = True  # Required for most movement actions

    def __init__(self, conn, robot_id, is_primary, **kw):
        super().__init__(**kw)
        #: :class:`cozmo.conn.CozmoConnectoin`: The active connection to the engine.
        self.conn = conn
        #: int: The internal ID number of the robot.
        self.robot_id = robot_id

        self._is_ready = False
        self._pose = None
        self.is_primary = is_primary

        #: :class:`cozmo.camera.Camera` Provides access to the robot's camera
        self.camera = self.camera_factory(self, dispatch_parent=self)

        #: :class:`cozmo.world.World` Tracks state information about Cozmo's world.
        self.world = self.world_factory(self.conn, self, dispatch_parent=self)

        self._action_dispatcher = self._action_dispatcher_factory(self)

        self.left_wheel_speed = None
        self.right_wheel_speed = None
        self.light_height = None
        self.battery_voltage = None
        self.carrying_object_id = -1
        self.carrying_object_on_top_id = -1
        self.head_tracking_object_id  = -1
        self.localized_to_object_id = -1
        self.last_image_time = None
        self._pose_angle = None
        self._pose_pitch = None
        self._head_angle = None
        self._robot_status_flags = 0
        self._game_status_flags = 0


        # send all received events to the world and action dispatcher
        self._add_child_dispatcher(self._action_dispatcher)
        self._add_child_dispatcher(self.world)


    #### Private Methods ####

    def _initialize(self):
        # Perform all steps necessary to initialize the robot and trigger
        # an EvtRobotReady event when complete.
        async def _init():
            # Note: Robot state is reset on entering SDK mode, and after any SDK program exits
            self.stop_all_motors()
            self.enable_reactionary_behaviors(False)

            # Ensure the SDK has full control of cube lights
            self._set_cube_light_state(False)

            await self.world.delete_all_custom_objects()
            self._reset_behavior_state()

            # wait for animations to load
            await self.conn.anim_names.wait_for_loaded()

            msg = _clad_to_engine_iface.GetBlockPoolMessage()
            self.conn.send_msg(msg)

            self._is_ready = True
            logger.info("Robot initialized OK")
            self.dispatch_event(EvtRobotReady, robot=self)
        asyncio.ensure_future(_init(), loop=self._loop)

    def _reset_behavior_state(self):
        msg = _clad_to_engine_iface.ExecuteBehavior(
                behaviorType=_clad_to_engine_cozmo.BehaviorType.NoneBehavior)
        self.conn.send_msg(msg)

    def _set_cube_light_state(self, enable):
        msg = _clad_to_engine_iface.EnableLightStates(enable=enable, objectID=-1)
        self.conn.send_msg(msg)

    #### Properties ####

    @property
    def is_ready(self):
        """bool: True if the robot has been initialized and is ready to accept commands."""
        return self._is_ready

    @property
    def anim_names(self):
        '''set of string: Set of all the available animation names

        An alias of :attr:`cozmo.conn.anim_names`.

        Generally animation triggers are preferred over explict animation names:
        See :class:`cozmo.anim.Triggers` for available animation triggers.
        '''
        return self.conn.anim_names

    @property
    def pose(self):
        """:class:`cozmo.util.Pose`: The current pose of cozmo relative to where he started when the engine was initialized.
        """
        return self._pose

    @property
    def is_moving(self):
        '''bool: True if Cozmo currently moving anything (head, lift or wheels/treads).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_MOVING) != 0

    @property
    def is_carrying_block(self):
        '''bool: True if Cozmo currently carrying a block.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_CARRYING_BLOCK) != 0

    @property
    def is_picking_or_placing(self):
        '''bool: True if Cozmo picking or placing something.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_PICKING_OR_PLACING) != 0

    @property
    def is_picked_up(self):
        '''bool: True if Cozmo currently picked up (in the air).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_PICKED_UP) != 0

    @property
    def is_falling(self):
        '''bool: True if Cozmo currently falling.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_FALLING) != 0

    @property
    def is_animating(self):
        '''bool: True if Cozmo currently playing an animation.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ANIMATING) != 0

    @property
    def is_animating_idle(self):
        '''bool: True if Cozmo currently playing an idle animation.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ANIMATING_IDLE) != 0

    @property
    def is_pathing(self):
        '''bool: True fi Cozmo currently traversing a path.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_PATHING) != 0

    @property
    def is_lift_in_pos(self):
        '''bool: True if Cozmo's lift in the desired position (False if still trying to move there).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.LIFT_IN_POS) != 0

    @property
    def is_head_in_pos(self):
        '''bool: True Cozmo's head in the desired position (False if still trying to move there).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.HEAD_IN_POS) != 0

    @property
    def is_anim_buffer_full(self):
        '''bool: True Is Cozmo's animation buffer full (on robot).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ANIM_BUFFER_FULL) != 0

    @property
    def is_on_charger(self):
        '''bool: True fi Cozmo currently on the charger.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ON_CHARGER) != 0

    @property
    def is_charging(self):
        '''bool: True if Cozmo currently charging.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_CHARGING) != 0

    @property
    def is_cliff_detected(self):
        '''bool: True if Cozmo detected a cliff (in front of the robot).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.CLIFF_DETECTED) != 0

    @property
    def are_wheels_moving(self):
        '''bool: True if Cozmo's wheels/treads are currently moving.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.ARE_WHEELS_MOVING) != 0

    @property
    def is_localized(self):
        '''bool: True if Cozmo is localized (i.e. knows where he is, and has both treads on the ground).'''
        return (self._game_status_flags & _clad_to_game_cozmo.GameStatusFlag.IsLocalized) != 0

    @property
    def pose_angle(self):
        ''':class:`cozmo.util.Angle`: Cozmo's pose angle (heading in X-Y plane).'''
        return self._pose_angle

    @property
    def pose_pitch(self):
        ''':class:`cozmo.util.Angle`: Cozmo's pose pitch (angle up/down).'''
        return self._pose_pitch

    @property
    def head_angle(self):
        ''':class:`cozmo.util.Angle`: Cozmo's head angle (up/down).'''
        return self._head_angle

    #### Private Event Handlers ####

    #def _recv_default_handler(self, event, **kw):
    #    msg = kw.get('msg')
    #    logger_protocol.debug("Robot received unhandled internal event_name=%s  kw=%s", event.event_name, kw)

    def recv_default_handler(self, event, **kw):
        logger.debug("Robot received unhandled public event=%s", event)

    def _recv_msg_processed_image(self, _, *, msg):
        pass

    def _recv_msg_image_chunk(self, evt, *, msg):
        self.camera.dispatch_event(evt)

    def _recv_msg_robot_state(self, evt, *, msg):
        self._pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                               q0=msg.pose.q0, q1=msg.pose.q1,
                               q2=msg.pose.q2, q3=msg.pose.q3)
        self._pose_angle = util.radians(msg.poseAngle_rad) # heading in X-Y plane
        self._pose_pitch = util.radians(msg.posePitch_rad)
        self._head_angle = util.radians(msg.headAngle_rad)
        self.left_wheel_speed  = util.speed_mmps(msg.leftWheelSpeed_mmps)
        self.right_wheel_speed = util.speed_mmps(msg.rightWheelSpeed_mmps)
        self.lift_height       = util.distance_mm(msg.liftHeight_mm)
        self.battery_voltage           = msg.batteryVoltage
        self.carrying_object_id        = msg.carryingObjectID      # int_32 will be -1 if not carrying object
        self.carrying_object_on_top_id = msg.carryingObjectOnTopID # int_32 will be -1 if no object on top of object being carried
        self.head_tracking_object_id   = msg.headTrackingObjectID  # int_32 will be -1 if head is not tracking to any object
        self.localized_to_object_id    = msg.localizedToObjectID   # int_32 Will be -1 if not localized to any object
        self.last_image_time           = msg.lastImageTimeStamp
        self._robot_status_flags       = msg.status     # uint_16 as bitflags - See _clad_to_game_cozmo.RobotStatusFlag
        self._game_status_flags        = msg.gameStatus # uint_8  as bitflags - See _clad_to_game_cozmo.GameStatusFlag

        if msg.robotID != self.robot_id:
            logger.error("robot ID changed mismatch (msg=%s, self=%s)", msg.robotID, self.robot_id )

    #### Public Event Handlers ####


    #### Commands ####

    def enable_reactionary_behaviors(self, should_enable):
        '''Enable or disable Cozmo's responses to being handled or observing the world.

        Args:
            should_enable (bool): True if the robot should react to its environment.
        '''
        msg = _clad_to_engine_iface.EnableReactionaryBehaviors(enabled=should_enable)
        self.conn.send_msg(msg)

    def set_robot_volume(self, robot_volume):
        '''Set the volume for the speaker in the robot.

        Args:
            robot_volume (float): The new volume (0.0 = mute, 1.0 = max).
        '''
        msg = _clad_to_engine_iface.SetRobotVolume(robotId=self.robot_id, volume=robot_volume)
        self.conn.send_msg(msg)

    def abort_all_actions(self):
        '''Abort all actions on this robot

        Abort / Cancel any action that is currently either running or queued within the engine
        '''
        # RobotActionType.UNKNOWN is a wildcard that matches all actions when cancelling.
        msg = _clad_to_engine_iface.CancelAction(robotId=self.robot_id,
                                                 actionType=_clad_to_engine_cozmo.RobotActionType.UNKNOWN)
        self.conn.send_msg(msg)

    ### Low-Level Commands ###

    async def drive_wheels(self, l_wheel_speed, r_wheel_speed,
                                 l_wheel_acc=None, r_wheel_acc=None, duration=None):
        '''Tell Cozmo to directly move his treads.

        Args:
            l_wheel_speed (float): Speed of the left tread (in millimeters per second)
            r_wheel_speed (float): Speed of the right tread (in millimeters per second)
            l_wheel_acc (float): Acceleration of left tread (in millimeters per second squared)
            None value defaults this to the same as l_wheel_speed
            r_wheel_acc (float): Acceleration of right tread (in millimeters per second squared)
            None value defaults this to the same as r_wheel_speed
            duration (float): Time for the robot to drive. Will call :meth:`~cozmo.robot.stop_all_motors`
            after this duration has passed
        '''
        if l_wheel_acc is None:
            l_wheel_acc = l_wheel_speed
        if r_wheel_acc is None:
            r_wheel_acc = r_wheel_speed

        msg = _clad_to_engine_iface.DriveWheels(lwheel_speed_mmps=l_wheel_speed,
                                                rwheel_speed_mmps=r_wheel_speed,
                                                lwheel_accel_mmps2=l_wheel_acc,
                                                rwheel_accel_mmps2=r_wheel_acc)

        self.conn.send_msg(msg)
        if duration:
            await asyncio.sleep(duration, loop=self._loop)
            self.stop_all_motors()

    def stop_all_motors(self):
        '''Tell Cozmo to stop all motors.'''
        msg = _clad_to_engine_iface.StopAllMotors()
        self.conn.send_msg(msg)

    def move_head(self, speed):
        '''Tell Cozmo's head motor to move with a certain speed.

        Positive speed for up, negative speed for down. Measured in radians per second.

        Args:
            speed (float): Motor speed for Cozmo's head, measured in radians per second.
        '''
        msg = _clad_to_engine_iface.MoveHead(speed_rad_per_sec=speed)
        self.conn.send_msg(msg)

    def move_lift(self, speed):
        '''Tell Cozmo's lift motor to move with a certain speed.

        Positive speed for up, negative speed for down.  Measured in radians per second.

        Args:
            speed (float): Motor speed for Cozmo's lift, measured in radians per second.
        '''
        msg = _clad_to_engine_iface.MoveLift()
        msg = _clad_to_engine_iface.MoveLift(speed_rad_per_sec=speed)
        self.conn.send_msg(msg)

    def say_text(self, text, play_excited_animation=False, use_cozmo_voice=True, duration_scalar=1.8, voice_pitch=0.0):
        '''Have Cozmo say text!

        Args:
            text (string): The words for Cozmo to say.
            play_excited_animation (bool): Whether to also play an excited
                animation while speaking (moves Cozmo a lot).
            use_cozmo_voice (bool): Whether to use Cozmo's robot voice
                (otherwise, he uses a generic human male voice).
            duration_scalar (float): Adjust the relative duration of the
                generated text to speech audio.
            voice_pitch (float): Adjust the pitch of Cozmo's robot voice [-1.0, 1.0]
        Returns:
            A :class:`cozmo.robot.SayText` action object which can be
                queried to see when it is complete
        '''

        action = self.say_text_factory(text=text, play_excited_animation=play_excited_animation,
                                       use_cozmo_voice=use_cozmo_voice, duration_scalar=duration_scalar,
                                       voice_pitch=voice_pitch, conn=self.conn,
                                       robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    def set_backpack_lights(self, light1, light2, light3, light4, light5):
        '''Set the lights on Cozmo's backpack.

        Args:
            light1-5 (class:'cozmo.lights.Light'): The lights for Cozmo's backpack.
        '''
        msg = _clad_to_engine_iface.SetBackpackLEDs(robotID=self.robot_id)
        for i, light in enumerate( (light1, light2, light3, light4, light5) ):
            if light is not None:
                lights._set_light(msg, i, light)

        self.conn.send_msg(msg)

    def set_all_backpack_lights(self, light):
        '''Set the lights on Cozmo's backpack to the same color.

        Args:
            light (class:'cozmo.lights.Light'): The lights for Cozmo's backpack.
        '''
        light_arr = [ light ] * 5
        self.set_backpack_lights(*light_arr)

    def set_backpack_lights_off(self):
        '''Set the lights on Cozmo's backpack to off.'''
        light_arr = [ lights.off_light ] * 5
        self.set_backpack_lights(*light_arr)

    def set_head_angle(self, angle, accel=10.0, max_speed=10.0, duration=0.0):
        '''Tell Cozmo's head to turn to a given angle.

        Args:
            angle: (:class:`cozmo.util.Angle`): Desired angle in radians for
                Cozmo's head. (:const:`MIN_HEAD_ANGLE` to
                :const:`MAX_HEAD_ANGLE`).
            accel (float): Acceleration of Cozmo's head in radians per second squared.
            max_speed (float): Maximum speed of Cozmo's head in radians per second.
            duration (float): Time for Cozmo's head to turn in seconds.
        Returns:
            A :class:`cozmo.robot.SetHeadAngle` action object which can be
                queried to see when it is complete
        '''
        action = self.set_head_angle_factory(angle=angle, max_speed=max_speed,
                accel=accel, duration=duration, conn=self.conn,
                robot=self, dispatch_parent=self)

        self._action_dispatcher._send_single_action(action)
        return action

    def set_lift_height(self, height, accel=1.0, max_speed=1.0, duration=2.0):
        '''Tell Cozmo's lift to move to a given height

        Args:
            height (float): desired height for Cozmo's lift 0.0 (bottom) to
                1.0 (top) (we clamp it to this range internally).
            accel (float): Acceleration of Cozmo's lift in radians per
                second squared.
            max_speed (float): Maximum speed of Cozmo's lift in radians per second.
            duration (float): Time for Cozmo's lift to move in seconds.
        Returns:
            A :class:`cozmo.robot.SetLiftHeight` action object which can be
                queried to see when it is complete.
        '''
        action = self.set_lift_height_factory(height=height, max_speed=max_speed,
                accel=accel, duration=duration, conn=self.conn,
                robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action


    ## Animation Commands ##

    def play_anim(self, name, loop_count=1):
        '''Starts an animation playing on a robot.

        Returns an Animation object as soon as the request to play the animation
        has been sent.  Call the wait_for_completed method on the animation
        if you wish to wait for completion (or listen for the
        :class:`cozmo.anim.EvtAnimationCompleted` event).

        Args:
            name (str): The name of the animation to play.
            loop_count (int): Number of times to play the animation.
        Returns:
            A :class:`cozmo.anim.Animation` action object which can be queried
                to see when it is complete.
        Raises:
            :class:`ValueError` if supplied an invalid animation name.
        '''
        if name not in self.conn.anim_names:
            raise ValueError('Unknown animation name "%s"' % name)
        action = self.animation_factory(name, loop_count,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    def play_anim_trigger(self, trigger, loop_count=1):
        """Starts an animation trigger playing on a robot.

        As noted in the Triggers class, playing a trigger requests that an
        animation of a certain class starts playing, rather than an exact
        animation name as influenced by the robot's mood, and other factors.

        Args:
            trigger (object): An attribute of the :class:`cozmo.anim.Triggers` class
            loop_count (int): Number of times to play the animation
        Returns:
            A :class:`cozmo.anim.AnimationTrigger` action object which can be
                queried to see when it is complete
        Raises:
            :class:`ValueError` if supplied an invalid animation trigger.
        """
        if not isinstance(trigger, anim._AnimTrigger):
            raise TypeError("Invalid trigger supplied")

        action = self.animation_trigger_factory(trigger, loop_count,
            conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    # Cozmo's Face animation commands

    def display_lcd_face_image(self, screen_data, duration_ms):
        ''' Display a bitmap image on Cozmo's LCD face screen.

        Args:
            screen_data (:class:`bytes`): a sequence of pixels (8 pixels per
                byte) (from e.g.
                :func:`cozmo.lcd_face.convert_pixels_to_screen_data`).
            duration_ms (float): time to keep displaying this image on Cozmo's
                face (clamped to 30 seconds in engine).
        '''
        msg = _clad_to_engine_iface.DisplayFaceImage(faceData=screen_data, duration_ms=duration_ms)
        self.conn.send_msg(msg)


    ## Behavior Commands ##

    def start_behavior(self, behavior_type):
        '''Starts executing a behavior.

        Call the :meth:`~cozmo.behavior.Behavior.stop` method on the behavior
        object at some point in the future to terminate execution.

        Args:
            behavior_type (:class:`cozmo.behavior._BehaviorType):  An attribute of
                :class:`cozmo.behavior.BehaviorTypes`.
        Returns:
            :class:`cozmo.behavior.Behavior`
        Raises:
            :class:`TypeError` if an invalid behavior type is supplied.
        '''
        if not isinstance(behavior_type, behavior._BehaviorType):
            raise TypeError('Invalid behavior supplied')
        b = self.behavior_factory(self, behavior_type, is_active=True, dispatch_parent=self)
        msg = _clad_to_engine_iface.ExecuteBehaviorByExecutableType(
                behaviorType=behavior_type.id)
        self.conn.send_msg(msg)
        return b

    async def run_timed_behavior(self, behavior_type, active_time):
        '''Executes a behavior for a set number of seconds.

        This call blocks and stops the behavior after active_time seconds.

        Args:
            behavior_type (:class:`cozmo.behavior._BehaviorType): An attribute of
                :class:`cozmo.behavior.BehaviorTypes`.
            active_time (float): specifies the time to execute in seconds
        Raises:
            :class:`TypeError` if an invalid behavior type is supplied.
        '''
        b = self.start_behavior(behavior_type)
        await asyncio.sleep(active_time, loop=self._loop)
        b.stop()


    ## Object Commands ##

    def pickup_object(self, obj, use_pre_dock_pose=True):
        '''Instruct the robot to pick-up the supplied object.

        Args:
            obj (:class:`cozmo.objects.ObservableObject`): The target object to
                pick up where ``obj.pickupable`` is True.
            use_pre_dock_pose (bool): whether or not to try to immediately pick
                up an object or first position the robot next to the object.
        Returns:
            A :class:`cozmo.robot.PickupObject` action object which can be
                queried to see when it is complete.
        Raises:
            :class:`cozmo.exceptions.RobotBusy` if another action is already running.
            :class:`cozmo.exceptions.NotPickupable` if object type can't be picked up.
        '''
        if not obj.pickupable:
            raise exceptions.NotPickupable('Cannot pickup this type of object')

        # TODO: Check with the World to see if Cozmo is already holding an object.
        logger.info("Sending pickup object request for object=%s", obj)
        action = self.pickup_object_factory(obj=obj, use_pre_dock_pose=use_pre_dock_pose,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    def place_on_object(self, obj, use_pre_dock_pose=True):
        '''Asks Cozmo to place the currently held object onto a target object.

        Args:
            obj (:class:`cozmo.objects.ObservableObject`): The target object to
                place current held object on, where obj.place_objects_on_this
                is True.
            use_pre_dock_pose (bool): Whether or not to try to immediately pick
                up an object or first position the robot next to the object.
        Returns:
            A :class:`cozmo.robot.PlaceOnObject` action object which can be
                queried to see when it is complete.
        Raises:
            :class:`cozmo.exceptions.RobotBusy` if another action is already running
            :class:`cozmo.exceptions.CannotPlaceObjectsOnThis` if the object cannot have objects
            placed on it.
        '''
        if not obj.place_objects_on_this:
            raise exceptions.CannotPlaceObjectsOnThis('Cannot place objects on this type of object')

        # TODO: Check with the World to see if Cozmo is already holding an object.
        logger.info("Sending place on object request for target object=%s", obj)
        action = self.place_on_object_factory(obj=obj, use_pre_dock_pose=use_pre_dock_pose,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    def place_object_on_ground_here(self, obj):
        '''Ask Cozmo to place the object he is carrying on the ground at the current location.

        Returns:
            A :class:`cozmo.robot.PlaceObjectOnGroundHere` action object which
                can be queried to see when it is complete.
        Raises:
            :class:`cozmo.exceptions.RobotBusy` if another action is already running
        '''
        # TODO: Check whether Cozmo is known to be holding the object in question
        logger.info("Sending place down here request for object=%s", obj)
        action = self.place_object_on_ground_here_factory(obj=obj,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action


    ## Interact with seen Face Commands ##

    def turn_towards_face(self, face):
        '''Tells Cozmo to turn towards this face.

        Args:
            face: (:class:`cozmo.faces.Face`): The face Cozmo will turn towards.
        Returns:
            A :class:`cozmo.robot.TurnTowardsFace` action object which can be
                queried to see when it is complete
        '''
        action = self.turn_towards_face_factory(face=face,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action


    ## Robot Driving Commands ##

    def go_to_pose(self, pose, relative_to_robot=False):
        '''Tells Cozmo to drive to the specified pose and orientation.

        If relative_to_robot is set to True, the given pose will assume the
        robot's pose as its origin.

        Since the robot understands position by monitoring its tread movement,
        it does not understand movement in the z axis. This means that the only
        applicable elements of pose in this situation are position.x position.y
        and rotation.angle_z.

        Args:
            pose: (:class:`cozmo.util.Pose`): The destination pose.
            relative_to_robot (bool): Whether the given pose is relative to
                the robot's pose.
        Returns:
            A :class:`cozmo.robot.GoToPose` action object which can be queried
                to see when it is complete.
        '''
        if relative_to_robot:
            pose = self.pose.define_pose_relative_this(pose)
        action = self.go_to_pose_factory(pose=pose,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    def turn_in_place(self, angle):
        '''Turn the robot around its current position.

        Args:
            angle: (:class:`cozmo.util.Angle`): The angle to turn.
        Returns:
            A :class:`cozmo.robot.TurnInPlace` action object which can be
                queried to see when it is complete.
        '''
        # TODO: add support for absolute vs relative positioning, speed & accel options
        action = self.turn_in_place_factory(angle=angle,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    def drive_off_charger_contacts(self):
        '''Tells Cozmo to drive forward slightly to get off the charger contacts.

        All motor movement is disabled while Cozmo is on the charger to
        prevent hardware damage. This command is the one exception and provides
        a way to drive forward a little to disconnect from the charger contacts
        and thereby re-enable all other commands.

        Returns:
           A :class:`cozmo.robot.DriveOffChargerContacts` action object which
            can be queried to see when it is complete.
        '''
        action = self.drive_off_charger_contacts_factory(conn=self.conn,
                robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action)
        return action

    def drive_straight(self, distance, speed, should_play_anim=True):
        '''Tells Cozmo to drive in a straight line

        Cozmo will drive for the specified distance (forwards or backwards)

        Args:
            distance (:class:`cozmo.util.Distance`): The distance to drive
                (>0 for forwards, <0 for backwards)
            speed (:class:`cozmo.util.Speed`): The speed to drive at
                (should always be >0, the abs(speed) is used internally)
            should_play_anim (bool): Whether to play idle animations
                whilst driving (tilt head, hum, animated eyes, etc.)

        Returns:
           A :class:`cozmo.robot.DriveStraight` action object which
            can be queried to see when it is complete.
        '''
        action = self.drive_straight_factory(conn=self.conn,
                                             robot=self,
                                             dispatch_parent=self,
                                             distance=distance,
                                             speed=speed,
                                             should_play_anim=should_play_anim)
        self._action_dispatcher._send_single_action(action)
        return action
