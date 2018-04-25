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
__all__ = ['MIN_HEAD_ANGLE', 'MAX_HEAD_ANGLE',
           'MIN_LIFT_HEIGHT', 'MIN_LIFT_HEIGHT_MM', 'MAX_LIFT_HEIGHT', 'MAX_LIFT_HEIGHT_MM',
           'MIN_LIFT_ANGLE', 'MAX_LIFT_ANGLE',
           # Event classes
           'EvtRobotReady', 'EvtRobotStateUpdated', 'EvtUnexpectedMovement',
           # Helper classes
           'LiftPosition', 'UnexpectedMovementSide', 'UnexpectedMovementType',
           # Robot Action classes
           'DisplayOledFaceImage', 'DockWithCube', 'DriveOffChargerContacts', 'DriveStraight',
           'GoToObject', 'GoToPose', 'PerformOffChargerContext', 'PickupObject',
           'PlaceObjectOnGroundHere', 'PlaceOnObject', 'PopAWheelie', 'RollCube', 'SayText',
           'SetHeadAngle', 'SetLiftHeight', 'TurnInPlace', 'TurnTowardsFace',
           # Robot
           'Robot']


import asyncio
import collections
import math
import warnings

from . import logger, logger_protocol
from . import action
from . import anim
from . import audio
from . import song
from . import behavior
from . import camera
from . import conn
from . import event
from . import exceptions
from . import lights
from . import objects
from . import util
from . import world
from . import robot_alignment

from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo, _clad_to_engine_anki, _clad_to_game_cozmo, CladEnumWrapper

#### Events

class EvtRobotReady(event.Event):
    '''Generated when the robot has been initialized and is ready for commands.'''
    robot = "Robot object representing the robot to command"


class EvtRobotStateUpdated(event.Event):
    '''Dispatched whenever the robot's state is updated (multiple times per second).'''
    robot = "Robot object representing the robot to command"


class EvtUnexpectedMovement(event.Event):
    '''Triggered whenever the robot does not move as expected (typically rotation).'''
    robot = "Robot object representing the robot to command"
    timestamp = "Robot timestamp for when the unexpected movement occurred"
    movement_type = "An UnexpectedMovementType Object representing the type of unexpected movement"
    movement_side = "An UnexpectedMovementSide Object representing the side that is obstructing movement"

#### Constants


#: The minimum angle the robot's head can be set to
MIN_HEAD_ANGLE = util.degrees(-25)

#: The maximum angle the robot's head can be set to
MAX_HEAD_ANGLE = util.degrees(44.5)

# The lowest height-above-ground that lift can be moved to in millimeters.
MIN_LIFT_HEIGHT_MM = 32.0

#: The lowest height-above-ground that lift can be moved to
MIN_LIFT_HEIGHT = util.distance_mm(MIN_LIFT_HEIGHT_MM)

# The largest height-above-ground that lift can be moved to in millimeters.
MAX_LIFT_HEIGHT_MM = 92.0

#: The largest height-above-ground that lift can be moved to
MAX_LIFT_HEIGHT = util.distance_mm(MAX_LIFT_HEIGHT_MM)

#: The length of Cozmo's lift arm
LIFT_ARM_LENGTH = util.distance_mm(66.0)

#: The height above ground of Cozmo's lift arm's pivot
LIFT_PIVOT_HEIGHT = util.distance_mm(45.0)

#: The minimum angle the robot's lift can be set to
MIN_LIFT_ANGLE = util.radians(math.asin((MIN_LIFT_HEIGHT_MM - LIFT_PIVOT_HEIGHT.distance_mm) / LIFT_ARM_LENGTH.distance_mm))

#: The maximum angle the robot's lift can be set to
MAX_LIFT_ANGLE = util.radians(math.asin((MAX_LIFT_HEIGHT_MM - LIFT_PIVOT_HEIGHT.distance_mm) / LIFT_ARM_LENGTH.distance_mm))


class LiftPosition:
    '''Represents the position of Cozmo's lift.

    The class allows the position to be referred to as either absolute height
    above the ground, as a ratio from 0.0 to 1.0, or as the angle of the lift
    arm relative to the ground.

    Args:
        height (:class:`cozmo.util.Distance`): The height of the lift above the ground.
        ratio (float): The ratio from 0.0 to 1.0 that the lift is raised from the ground.
        angle (:class:`cozmo.util.Angle`): The angle of the lift arm relative to the ground.
    '''
    __slots__ = ('_height')

    def __init__(self, height=None, ratio=None, angle=None):
        def _count_arg(arg):
            # return 1 if argument is set (not None), 0 otherwise
            return 0 if (arg is None) else 1
        num_provided_args = _count_arg(height) + _count_arg(ratio) + _count_arg(angle)
        if num_provided_args != 1:
            raise ValueError("Expected one, and only one, of the distance, ratio or angle keyword arguments")

        if height is not None:
            if not isinstance(height, util.Distance):
                raise TypeError("Unsupported type for distance - expected util.Distance")
            self._height = height
        elif ratio is not None:
            height_mm = MIN_LIFT_HEIGHT_MM + (ratio * (MAX_LIFT_HEIGHT_MM - MIN_LIFT_HEIGHT_MM))
            self._height = util.distance_mm(height_mm)
        elif angle is not None:
            if not isinstance(angle, util.Angle):
                raise TypeError("Unsupported type for angle - expected util.Angle")
            height_mm = (math.sin(angle.radians) * LIFT_ARM_LENGTH.distance_mm) + LIFT_PIVOT_HEIGHT.distance_mm
            self._height = util.distance_mm(height_mm)

    def __repr__(self):
        return "<%s height=%s ratio=%s angle=%s>" % (self.__class__.__name__, self._height, self.ratio, self.angle)

    @property
    def height(self):
        ''':class:`cozmo.util.Distance`: The height above the ground.'''
        return self._height

    @property
    def ratio(self):
        '''float: The ratio from 0 to 1 that the lift is raised, 0 at the bottom, 1 at the top.'''
        ratio = ((self._height.distance_mm - MIN_LIFT_HEIGHT_MM) /
                 (MAX_LIFT_HEIGHT_MM - MIN_LIFT_HEIGHT_MM))
        return ratio

    @property
    def angle(self):
        ''':class:`cozmo.util.Angle`: The angle of the lift arm relative to the ground.'''
        sin_angle = (self._height.distance_mm - LIFT_PIVOT_HEIGHT.distance_mm) / LIFT_ARM_LENGTH.distance_mm
        angle_radians = math.asin(sin_angle)
        return util.radians(angle_radians)


#### Actions

class GoToPose(action.Action):
    '''Represents the go to pose action in progress.

    Returned by :meth:`~cozmo.robot.Robot.go_to_pose`
    '''
    def __init__(self, pose, **kw):
        super().__init__(**kw)
        self.pose = pose

    def _repr_values(self):
        return "pose=%s" % (self.pose)

    def _encode(self):
        return _clad_to_engine_iface.GotoPose(x_mm=self.pose.position.x,
                                              y_mm=self.pose.position.y,
                                              rad=self.pose.rotation.angle_z.radians)


class GoToObject(action.Action):
    '''Represents the go to object action in progress.

    Returned by :meth:`~cozmo.robot.Robot.go_to_object`
    '''
    def __init__(self, object_id, distance_from_object, **kw):
        super().__init__(**kw)
        self.object_id = object_id
        self.distance_from_object = distance_from_object

    def _repr_values(self):
        return "object_id=%s, distance_from_object=%s" % (self.object_id, self.distance_from_object)

    def _encode(self):
        return _clad_to_engine_iface.GotoObject(objectID=self.object_id,
                                                distanceFromObjectOrigin_mm=self.distance_from_object.distance_mm,
                                                useManualSpeed=False,
                                                usePreDockPose=False)

class DockWithCube(action.Action):
    '''Represents the dock with cube action in progress.

    Returned by :meth:`~cozmo.robot.Robot.dock_with_cube`
    '''
    def __init__(self, obj, approach_angle, alignment_type, distance_from_marker, **kw):
        super().__init__(**kw)
        #: The object (e.g. an instance of :class:`cozmo.objects.LightCube`) that is being put down
        self.obj = obj
        self.alignment_type = alignment_type
        if approach_angle is None:
            self.use_approach_angle = False
            self.approach_angle = util.degrees(0)
        else:
            self.use_approach_angle = True
            self.approach_angle = approach_angle

        if distance_from_marker is None:
            self.distance_from_marker = util.distance_mm(0)
        else:
            self.distance_from_marker = distance_from_marker

    def _repr_values(self):
        return "object=%s" % (self.obj)

    def _encode(self):
        return _clad_to_engine_iface.AlignWithObject(objectID=self.obj.object_id,
                                                     distanceFromMarker_mm=self.distance_from_marker.distance_mm,
                                                     approachAngle_rad=self.approach_angle.radians,
                                                     alignmentType=self.alignment_type.id,
                                                     useApproachAngle=self.use_approach_angle,
                                                     usePreDockPose=self.use_approach_angle,
                                                     useManualSpeed=False)

class RollCube(action.Action):
    '''Represents the roll cube action in progress.

    Returned by :meth:`~cozmo.robot.Robot.roll_cube`
    '''
    def __init__(self, obj, approach_angle, check_for_object_on_top, **kw):
        super().__init__(**kw)
        #: The object (e.g. an instance of :class:`cozmo.objects.LightCube`) that is being put down
        self.obj = obj
        #: bool: whether to check if there is an object on top
        self.check_for_object_on_top = check_for_object_on_top
        if approach_angle is None:
            self.use_approach_angle = False
            self.approach_angle = util.degrees(0)
        else:
            self.use_approach_angle = True
            self.approach_angle = approach_angle

    def _repr_values(self):
        return "object=%s, check_for_object_on_top=%s, approach_angle=%s" % (self.obj, self.check_for_object_on_top, self.approach_angle)

    def _encode(self):
        return _clad_to_engine_iface.RollObject(objectID=self.obj.object_id,
                                                approachAngle_rad=self.approach_angle.radians,
                                                useApproachAngle=self.use_approach_angle,
                                                usePreDockPose=self.use_approach_angle,
                                                useManualSpeed=False,
                                                checkForObjectOnTop=self.check_for_object_on_top)

class DriveOffChargerContacts(action.Action):
    '''Represents the drive off charger contacts action in progress.

    Returned by :meth:`~cozmo.robot.Robot.drive_off_charger_contacts`
    '''
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


class DisplayOledFaceImage(action.Action):
    '''Represents the "display oled face image" action in progress.

    Returned by :meth:`~cozmo.robot.Robot.display_oled_face_image`
    '''
    # Face images are sent so frequently, with the previous face image always
    # aborted, that logging each event would spam the log.
    _enable_abort_logging = False

    def __init__(self, screen_data, duration_ms, **kw):
        super().__init__(**kw)
        #: :class:`bytes`: a sequence of pixels (8 pixels per byte)
        self.screen_data = screen_data
        #: float: time to keep displaying this image on Cozmo's face
        self.duration_ms = duration_ms

    def _repr_values(self):
        return "screen_data=%s Bytes duration_ms=%s" %\
               (len(self.screen_data), self.duration_ms)

    def _encode(self):
        return _clad_to_engine_iface.DisplayFaceImage(faceData=self.screen_data,
                                                      duration_ms=self.duration_ms)


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
            self.say_style = _clad_to_engine_cozmo.SayTextVoiceStyle.CozmoProcessing_Sentence
        else:
            # default male human voice
            self.say_style = _clad_to_engine_cozmo.SayTextVoiceStyle.Unprocessed

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
                                             voicePitch=self.voice_pitch,
                                             fitToDuration=False)


class SetHeadAngle(action.Action):
    '''Represents the Set Head Angle action in progress.
       Returned by :meth:`~cozmo.robot.Robot.set_head_angle`
    '''
    def __init__(self, angle, max_speed, accel, duration, warn_on_clamp, **kw):
        super().__init__(**kw)

        if angle < MIN_HEAD_ANGLE:
            if warn_on_clamp:
                logger.warning("Clamping head angle from %s to min %s" % (angle, MIN_HEAD_ANGLE))
            self.angle = MIN_HEAD_ANGLE
        elif angle > MAX_HEAD_ANGLE:
            if warn_on_clamp:
                logger.warning("Clamping head angle from %s to max %s" % (angle, MAX_HEAD_ANGLE))
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
    def __init__(self, height, max_speed, accel, duration, **kw):
        super().__init__(**kw)

        if height < 0.0:
            logger.warning("lift height %s too small, should be in 0..1 range - clamping", height)
            self.lift_height_mm = MIN_LIFT_HEIGHT_MM
        elif height > 1.0:
            logger.warning("lift height %s too large, should be in 0..1 range - clamping", height)
            self.lift_height_mm = MAX_LIFT_HEIGHT_MM
        else:
            self.lift_height_mm = MIN_LIFT_HEIGHT_MM + (height * (MAX_LIFT_HEIGHT_MM - MIN_LIFT_HEIGHT_MM))

        #: float: Maximum speed of Cozmo's lift in radians per second
        self.max_speed = max_speed

        #: float: Acceleration of Cozmo's lift in radians per second squared
        self.accel = accel

        #: float: Time for Cozmo's lift to turn in seconds
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
    def __init__(self, angle, speed, accel, angle_tolerance, is_absolute, **kw):
        super().__init__(**kw)
        #: :class:`cozmo.util.Angle`: The angle to turn
        self.angle = angle
        #: :class:`cozmo.util.Angle`: Angular turn speed (per second).
        self.speed = speed
        #: :class:`cozmo.util.Angle`: Acceleration of angular turn (per second squared).
        self.accel = accel
        #: :class:`cozmo.util.Angle`: The minimum angular tolerance to consider
        #: the action complete (this is clamped to a minimum of 2 degrees internally).
        self.angle_tolerance = angle_tolerance
        #: bool: True to turn to a specific angle, False to turn relative to the current pose.
        self.is_absolute = is_absolute

    def _repr_values(self):
        return "angle=%s, speed=%s, accel=%s, tolerance=%s is_absolute=%s" %\
               (self.angle, self.speed, self.accel, self.angle_tolerance, self.is_absolute)

    def _get_radians(self, in_angle, default_value=0.0):
        # Helper method to allow None angles to represent default values
        if in_angle is None:
            return default_value
        else:
            return in_angle.radians

    def _encode(self):
        return _clad_to_engine_iface.TurnInPlace(
            angle_rad = self.angle.radians,
            speed_rad_per_sec = self._get_radians(self.speed),
            accel_rad_per_sec2 = self._get_radians(self.accel),
            tol_rad = self._get_radians(self.angle_tolerance),
            isAbsolute = int(self.is_absolute))


class PopAWheelie(action.Action):
    '''Tracks the progress of a "pop a wheelie" robot action.

    Returned by :meth:`~cozmo.robot.Robot.pop_a_wheelie`
    '''
    def __init__(self, obj, approach_angle, **kw):
        super().__init__(**kw)
        #: An object (e.g. an instance of :class:`cozmo.objects.LightCube`)
        #: being used as leverage to push cozmo on his back
        self.obj = obj
        if approach_angle is None:
            self.use_approach_angle = False
            self.approach_angle = util.degrees(0)
        else:
            self.use_approach_angle = True
            self.approach_angle = approach_angle

    def _repr_values(self):
        return ("object=%s, use_approach_angle=%s, approach_angle=%s" %
            (self.obj, self.use_approach_angle, self.approach_angle) )

    def _encode(self):
        return _clad_to_engine_iface.PopAWheelie(
            objectID=self.obj.object_id,
            approachAngle_rad=self.approach_angle.radians,
            useApproachAngle=self.use_approach_angle,
            usePreDockPose=self.use_approach_angle,
            useManualSpeed=False)


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
            faceID=self.face.face_id,
            maxTurnAngle_rad=util.degrees(180).radians)



class PerformOffChargerContext(event.Dispatcher):
    '''A helper class to provide a context manager to do operations while Cozmo is off charger.'''
    def __init__(self, robot, **kw):
        super().__init__(**kw)
        self.robot = robot

    async def __aenter__(self):
        self.was_on_charger = self.robot.is_on_charger
        if self.was_on_charger:
            await self.robot.drive_off_charger_contacts(in_parallel=True).wait_for_completed()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.was_on_charger:
            await self.robot.backup_onto_charger()
        return False


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
    #: :class:`TurnInPlace` class or subclass instance.
    turn_in_place_factory = TurnInPlace

    #: callable: The factory function that returns a
    #: :class:`TurnTowardsFace` class or subclass instance.
    turn_towards_face_factory = TurnTowardsFace

    #: callable: The factory function that returns a
    #: :class:`PickupObject` class or subclass instance.
    pickup_object_factory = PickupObject

    #: callable: The factory function that returns a
    #: :class:`PlaceOnObject` class or subclass instance.
    place_on_object_factory = PlaceOnObject

    #: callable: The factory function that returns a
    #: :class:`GoToPose` class or subclass instance.
    go_to_pose_factory = GoToPose

    #: callable: The factory function that returns a
    #: :class:`GoToObject` class or subclass instance.
    go_to_object_factory = GoToObject

    #: callable: The factory function that returns a
    #: :class:`DockWithCube` class or subclass instance.
    dock_with_cube_factory = DockWithCube

    #: callable: The factory function that returns a
    #: :class:`RollCube` class or subclass instance.
    roll_cube_factory = RollCube

    #: callable: The factory function that returns a
    #: :class:`PlaceObjectOnGroundHere` class or subclass instance.
    place_object_on_ground_here_factory = PlaceObjectOnGroundHere

    #: callable: The factory function that returns a
    #: :class:`PopAWheelie` class or subclass instance.
    pop_a_wheelie_factory = PopAWheelie

    #: callable: The factory function that returns a
    #: :class:`SayText` class or subclass instance.
    say_text_factory = SayText

    #: callable: The factory function that returns a
    #: :class:`SetHeadAngle` class or subclass instance.
    set_head_angle_factory = SetHeadAngle

    #: callable: The factory function that returns a
    #: :class:`SetLiftHeight` class or subclass instance.
    set_lift_height_factory = SetLiftHeight

    #: callable: The factory function that returns a
    #: :class:`DriveOffChargerContacts` class or subclass instance.
    drive_off_charger_contacts_factory = DriveOffChargerContacts

    #: callable: The factory function that returns a
    #: :class:`DriveStraight` class or subclass instance.
    drive_straight_factory = DriveStraight

    #: callable: The factory function that returns a
    #: :class:`DisplayOledFaceImage` class or subclass instance.
    display_oled_face_image_factory = DisplayOledFaceImage

    # other factories

    #: callable: The factory function that returns a
    #: :class:`cozmo.anim.Animation` class or subclass instance.
    animation_factory = anim.Animation

    #: callable: The factory function that returns a
    #: :class:`cozmo.anim.AnimationTrigger` class or subclass instance.
    animation_trigger_factory = anim.AnimationTrigger

    #: callable: The factory function that returns a
    #: :class:`cozmo.behavior.Behavior` class or subclass instance.
    behavior_factory = behavior.Behavior

    #: callable: The factory function that returns a
    #: :class:`cozmo.camera.Camera` class or subclass instance.
    camera_factory = camera.Camera

    #: callable: The factory function that returns a
    #: :class:`cozmo.robot.PerformOffChargerContext` class or subclass instance.
    perform_off_charger_factory = PerformOffChargerContext

    #: callable: The factory function that returns a
    #: :class:`cozmo.world.World` class or subclass instance.
    world_factory = world.World

    # other attributes

    #: bool: Set to True if the robot should drive off the charger as soon
    #: as the SDK connects to the engine.  Defaults to True.
    drive_off_charger_on_connect = True  # Required for most movement actions

    _current_behavior = None  # type: Behavior
    _is_freeplay_mode_active = False

    def __init__(self, conn, robot_id: int, is_primary: bool, **kw):
        super().__init__(**kw)
        #: :class:`cozmo.conn.CozmoConnection`: The active connection to the engine.
        self.conn = conn  # type: conn.CozmoConnection
        #: int: The internal ID number of the robot.
        self.robot_id = robot_id

        self._is_ready = False
        self._pose = None  # type: util.Pose
        #: bool: Specifies that this is the primary robot (always True currently)
        self.is_primary = is_primary

        #: :class:`cozmo.camera.Camera`: Provides access to the robot's camera
        self.camera = self.camera_factory(self, dispatch_parent=self)

        #: :class:`cozmo.world.World`: Tracks state information about Cozmo's world.
        self.world = self.world_factory(self.conn, self, dispatch_parent=self)

        self._action_dispatcher = self._action_dispatcher_factory(self)

        self._current_face_image_action = None  # type: DisplayOledFaceImage

        #: :class:`cozmo.util.Speed`: Speed of the left wheel
        self.left_wheel_speed = None  # type: util.Speed
        #: :class:`cozmo.util.Speed`: Speed of the right wheel
        self.right_wheel_speed = None  # type: util.Speed
        self._lift_position = LiftPosition(height=util.distance_mm(MIN_LIFT_HEIGHT_MM))
        #: float: The current battery voltage (not linear, but < 3.5 is low)
        self.battery_voltage = None  # type: float

        #: :class:`cozmo.util.Vector3`: The current accelerometer reading (x,y,z)
        #: In mm/s^2, measured in Cozmo's head (e.g. x=0 when Cozmo's head is level
        #: but x = z = ~7000 mm/s^2 when Cozmo's head is angled 45 degrees up)
        self.accelerometer = None  # type: util.Vector3

        self._is_device_accelerometer_supported = None  # type: bool
        self._is_device_gyro_supported = None  # type: bool

        #: :class:`cozmo.util.Vector3`: The current accelerometer reading for
        #: the connected mobile device. Requires that you have first called
        #: :meth:`enable_device_imu` with `enable_raw = True`. See
        #: :attr:`device_accel_user` for a user-filtered equivalent.
        self.device_accel_raw = None  # type: util.Vector3

        #: :class:`cozmo.util.Vector3`: The current user-filtered accelerometer
        #: reading for the connected mobile device. Requires that you have first
        #: called :meth:`enable_device_imu` with `enable_user = True`. This
        #: filtered version removes the constant acceleration from Gravity. See
        #: :attr:`device_accel_raw` for a raw version.
        self.device_accel_user = None  # type: util.Vector3

        #: :class:`cozmo.util.Quaternion`: The current gyro reading for
        #: the connected mobile device. Requires that you have first called
        #: :meth:`enable_device_imu` with `enable_gyro = True`
        self.device_gyro = None  # type: util.Quaternion

        #: :class:`cozmo.util.Vector3`: The current gyro reading (x,y,z)
        #: In radians/s, measured in Cozmo's head.
        #: Therefore a large value in a given component would indicate Cozmo is
        #: being rotated around that axis (where x=forward, y=left, z=up), e.g.
        #: y = -5 would indicate that Cozmo is being rolled onto his back
        self.gyro = None  # type: util.Vector3

        #: int: The ID of the object currently being carried (-1 if none)
        self.carrying_object_id = -1
        #: int: The ID of the object on top of the object currently being carried (-1 if none)
        self.carrying_object_on_top_id = -1
        #: int: The ID of the object the head is tracking to (-1 if none)
        self.head_tracking_object_id  = -1
        #: int: The ID of the object that the robot is localized to (-1 if none)
        self.localized_to_object_id = -1
        #: int: The robot's timestamp for the last image seen.
        #: ``None`` if no image was received yet.
        #: In milliseconds relative to robot epoch.
        self.last_image_robot_timestamp = None  # type: int
        self._pose_angle = None  # type: util.Angle
        self._pose_pitch = None  # type: util.Angle
        self._head_angle = None  # type: util.Angle
        self._robot_status_flags = 0
        self._game_status_flags = 0

        self._serial_number_head = 0
        self._serial_number_body = 0
        self._model_number = 0
        self._hw_version = 0

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
            self.enable_all_reaction_triggers(False)
            self.enable_stop_on_cliff(True)
            self._set_none_behavior()

            # Default to no memory map data being streamed
            self.world.request_nav_memory_map(-1.0)

            # Default to no device IMU data being streamed
            self.enable_device_imu(False, False, False)

            # Ensure the SDK has full control of cube lights
            self._set_cube_light_state(False)

            await self.world.delete_all_custom_objects()

            # wait for animations to load
            await self.conn.anim_names.wait_for_loaded()

            msg = _clad_to_engine_iface.GetBlockPoolMessage()
            self.conn.send_msg(msg)

            self._is_ready = True
            logger.info('Robot id=%s serial=%s initialized OK', self.robot_id, self.serial)
            self.dispatch_event(EvtRobotReady, robot=self)

            self._idle_stack_depth = 0
            self.set_idle_animation(anim.Triggers.Count)
        asyncio.ensure_future(_init(), loop=self._loop)

    def _set_none_behavior(self):
        # Internal helper method called from Behavior.stop etc.
        msg = _clad_to_engine_iface.ExecuteBehaviorByExecutableType(
                behaviorType=_clad_to_engine_cozmo.ExecutableBehaviorType.Wait)
        self.conn.send_msg(msg)
        if self._current_behavior is not None:
            self._current_behavior._set_stopped()

    def _set_cube_light_state(self, enable):
        msg = _clad_to_engine_iface.EnableLightStates(enable=enable, objectID=-1)
        self.conn.send_msg(msg)

    def _enable_cube_sleep(self, enable=True, skip_animation=True):
        # skip_animation (bool): True to skip the fadeout part of the sleep anim
        msg = _clad_to_engine_iface.EnableCubeSleep(enable=enable,
                                                    skipAnimation=skip_animation)
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
    def anim_triggers(self):
        '''list of :class:`cozmo.anim.Triggers`, specifying available animation triggers

        These can be sent to the play_anim_trigger to make the robot perform animations.

        An alias of :attr:`cozmo.anim.Triggers.trigger_list`.
        '''
        return anim.Triggers.trigger_list

    @property
    def pose(self):
        """:class:`cozmo.util.Pose`: The current pose (position and orientation) of Cozmo
        """
        return self._pose

    @property
    def is_moving(self):
        '''bool: True if Cozmo is currently moving anything (head, lift or wheels/treads).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_MOVING) != 0

    @property
    def is_carrying_block(self):
        '''bool: True if Cozmo is currently carrying a block.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_CARRYING_BLOCK) != 0

    @property
    def is_picking_or_placing(self):
        '''bool: True if Cozmo is picking or placing something.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_PICKING_OR_PLACING) != 0

    @property
    def is_picked_up(self):
        '''bool: True if Cozmo is currently picked up (in the air).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_PICKED_UP) != 0

    @property
    def is_falling(self):
        '''bool: True if Cozmo is currently falling.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_FALLING) != 0

    @property
    def is_animating(self):
        '''bool: True if Cozmo is currently playing an animation.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ANIMATING) != 0

    @property
    def is_animating_idle(self):
        '''bool: True if Cozmo is currently playing an idle animation.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ANIMATING_IDLE) != 0

    @property
    def is_pathing(self):
        '''bool: True if Cozmo is currently traversing a path.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_PATHING) != 0

    @property
    def is_lift_in_pos(self):
        '''bool: True if Cozmo's lift is in the desired position (False if still trying to move there).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.LIFT_IN_POS) != 0

    @property
    def is_head_in_pos(self):
        '''bool: True if Cozmo's head is in the desired position (False if still trying to move there).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.HEAD_IN_POS) != 0

    @property
    def is_anim_buffer_full(self):
        '''bool: True if Cozmo's animation buffer is full (on robot).'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ANIM_BUFFER_FULL) != 0

    @property
    def is_on_charger(self):
        '''bool: True if Cozmo is currently on the charger.'''
        return (self._robot_status_flags & _clad_to_game_cozmo.RobotStatusFlag.IS_ON_CHARGER) != 0

    @property
    def is_charging(self):
        '''bool: True if Cozmo is currently charging.'''
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
        '''bool: True if Cozmo is localized (i.e. knows where he is with respect to a cube, and has both treads on the ground).'''
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

    @property
    def lift_position(self):
        ''':class:`LiftPosition`: The position of Cozmo's lift.'''
        return self._lift_position

    @property
    def lift_height(self):
        ''':class:`cozmo.util.Distance`: Height of Cozmo's lift from the ground.

        In :const:`MIN_LIFT_HEIGHT` to :const:`MAX_LIFT_HEIGHT` range.
        '''
        return self._lift_position.height

    @property
    def lift_ratio(self):
        '''float: Ratio from 0 to 1 of how high Cozmo's lift is.'''
        return self._lift_position.ratio

    @property
    def lift_angle(self):
        ''':class:`cozmo.util.Angle`: Angle of Cozmo's lift relative to the ground.

        In :const:`MIN_LIFT_ANGLE` to :const:`MAX_LIFT_ANGLE` range.
        '''
        return self._lift_position.angle

    @property
    def current_behavior(self):
        ''':class:`cozmo.behavior.Behavior`: Cozmo's currently active behavior.'''
        if self._current_behavior is not None and self._current_behavior.is_active:
            return self._current_behavior
        else:
            return None

    @property
    def is_behavior_running(self):
        '''bool: True if Cozmo is currently running a behavior.

        When Cozmo is running a behavior he will behave fairly autonomously
        (playing animations and other actions as desired). Attempting to drive
        Cozmo whilst in this mode will likely have unexpected behavior on
        the robot and confuse Cozmo.
        '''
        return (self.is_freeplay_mode_active or
                (self._current_behavior is not None and self._current_behavior.is_active))

    @property
    def is_freeplay_mode_active(self):
        '''bool: True if Cozmo is in freeplay mode.

        When Cozmo is in freeplay mode he will behave autonomously (playing
        behaviors, animations and other actions as desired). Attempting to
        drive Cozmo whilst in this mode will likely have unexpected behavior
        on the robot and confuse Cozmo.
        '''
        return self._is_freeplay_mode_active

    @property
    def has_in_progress_actions(self):
        '''bool: True if Cozmo has any SDK-triggered actions still in progress.'''
        return self._action_dispatcher.has_in_progress_actions

    @property
    def camera_config(self):
        ''':class:`cozmo.robot.CameraConfig`: The read-only config/calibration for this robot's camera

        .. deprecated:: 0.12.0
           Use: :meth:`cozmo.camera.Camera.config` instead.
        '''
        warnings.warn("The 'robot.camera_config' method is deprecated, "
                      "use 'robot.camera.config' instead", DeprecationWarning, stacklevel=2)
        return self.camera.config

    @property
    def serial(self):
        '''string: The serial number, as a hex-string (e.g "02e08032"), for the robot.

        This matches the Cozmo Serial value in the About section of the settings
        menu in the app.
        '''
        return "%08x" % self._serial_number_body

    @property
    def is_device_accelerometer_supported(self):
        """bool: True if the attached mobile device supports accelerometer data."""
        return self._is_device_accelerometer_supported

    @property
    def is_device_gyro_supported(self):
        """bool: True if the attached mobile device supports gyro data."""
        return self._is_device_gyro_supported

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

    def _recv_msg_current_camera_params(self, evt, *, msg):
        self.camera.dispatch_event(evt)

    def _recv_msg_robot_observed_motion(self, evt, *, msg):
        self.camera.dispatch_event(evt)

    def _recv_msg_per_robot_settings(self, evt, *, msg):
        self._serial_number_head = msg.serialNumberHead
        self._serial_number_body = msg.serialNumberBody
        self._model_number = msg.modelNumber
        self._hw_version = msg.hwVersion
        self.camera._set_config(msg.cameraConfig)

    def _recv_msg_unexpected_movement(self, evt, *, msg):
        movement_type = UnexpectedMovementType.find_by_id(msg.movementType)
        movement_side = UnexpectedMovementSide.find_by_id(msg.movementSide)
        self.dispatch_event(EvtUnexpectedMovement, robot=self, timestamp=msg.timestamp, 
                            movement_type=movement_type, movement_side=movement_side)

    def _recv_msg_robot_state(self, evt, *, msg):
        self._pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                               q0=msg.pose.q0, q1=msg.pose.q1,
                               q2=msg.pose.q2, q3=msg.pose.q3,
                               origin_id=msg.pose.originID)
        self._pose_angle = util.radians(msg.poseAngle_rad) # heading in X-Y plane
        self._pose_pitch = util.radians(msg.posePitch_rad)
        self._head_angle = util.radians(msg.headAngle_rad)
        self.left_wheel_speed = util.speed_mmps(msg.leftWheelSpeed_mmps)
        self.right_wheel_speed = util.speed_mmps(msg.rightWheelSpeed_mmps)
        self._lift_position = LiftPosition(height=util.distance_mm(msg.liftHeight_mm))
        self.battery_voltage = msg.batteryVoltage
        self.accelerometer = util.Vector3(msg.accel.x, msg.accel.y, msg.accel.z)
        self.gyro = util.Vector3(msg.gyro.x, msg.gyro.y, msg.gyro.z)
        self.carrying_object_id = msg.carryingObjectID  # int_32 will be -1 if not carrying object
        self.carrying_object_on_top_id = msg.carryingObjectOnTopID  # int_32 will be -1 if no object on top of object being carried
        self.head_tracking_object_id = msg.headTrackingObjectID  # int_32 will be -1 if head is not tracking to any object
        self.localized_to_object_id = msg.localizedToObjectID  # int_32 Will be -1 if not localized to any object
        self.last_image_robot_timestamp = msg.lastImageTimeStamp
        self._robot_status_flags = msg.status  # uint_16 as bitflags - See _clad_to_game_cozmo.RobotStatusFlag
        self._game_status_flags = msg.gameStatus  # uint_8  as bitflags - See _clad_to_game_cozmo.GameStatusFlag

        self.dispatch_event(EvtRobotStateUpdated, robot=self)

    def _recv_msg_behavior_transition(self, evt, *, msg):
        new_type = behavior.BehaviorTypes.find_by_id(msg.newBehaviorExecType)
        if self._current_behavior is not None:
            if new_type == self._current_behavior.type:
                self._current_behavior._on_engine_started()
            else:
                self._current_behavior._set_stopped()

    # Device IMU

    def _recv_msg_device_accelerometer_values_raw(self, evt, *, msg):
        self.device_accel_raw = util.Vector3(msg.x_gForce, msg.y_gForce, msg.z_gForce)

    def _recv_msg_device_accelerometer_values_user(self, evt, *, msg):
        self.device_accel_user = util.Vector3(msg.x_gForce, msg.y_gForce, msg.z_gForce)

    def _recv_msg_device_gyro_values(self, evt, *, msg):
        self.device_gyro = util.Quaternion(msg.w, msg.x, msg.y, msg.z)

    def _recv_msg_is_device_imu_supported(self, evt, *, msg):
        self._is_device_accelerometer_supported = msg.isAccelerometerSupported
        self._is_device_gyro_supported = msg.isGyroSupported
        logger.debug("Mobile Device IMU support: accelerometer=%s gyro=%s",
                    self._is_device_accelerometer_supported, self._is_device_gyro_supported)

    #### Public Event Handlers ####


    #### Commands ####

    def enable_all_reaction_triggers(self, should_enable):
        '''Enable or disable Cozmo's responses to being handled or observing the world.

        Args:
            should_enable (bool): True if the robot should react to its environment.
        '''
        if should_enable:
            msg = _clad_to_engine_iface.RemoveDisableReactionsLock("sdk")
            self.conn.send_msg(msg)
        else:
            msg = _clad_to_engine_iface.DisableAllReactionsWithLock("sdk")
            self.conn.send_msg(msg)

    def enable_stop_on_cliff(self, enable):
        '''Enable or disable Cozmo's ability to drive off a cliff.

        Args:
            enable (bool): True if the robot should stop moving when a cliff is encountered.
        '''
        msg = _clad_to_engine_iface.EnableStopOnCliff(enable=enable)
        self.conn.send_msg(msg)

    def set_robot_volume(self, robot_volume):
        '''Set the volume for the speaker in the robot.

        Args:
            robot_volume (float): The new volume (0.0 = mute, 1.0 = max).
        '''
        msg = _clad_to_engine_iface.SetRobotVolume(robotId=self.robot_id, volume=robot_volume)
        self.conn.send_msg(msg)

    def abort_all_actions(self, log_abort_messages=False):
        '''Abort all actions on this robot

        Args:
            log_abort_messages (bool): True to log info on every action that
                is aborted.

        Abort / Cancel any action that is currently either running or queued within the engine
        '''
        self._action_dispatcher._abort_all_actions(log_abort_messages)

    def enable_facial_expression_estimation(self, enable=True):
        '''Enable or Disable facial expression estimation

        Cozmo can optionally estimate the facial expression for human faces to
        see if he thinks they're happy, sad, etc.

        Args:
            enable (bool): True to enable facial expression estimation, False to
                disable it. By default Cozmo starts with it disabled to save on
                processing time.
        '''

        msg = _clad_to_engine_iface.EnableVisionMode(
            mode=_clad_to_engine_cozmo.VisionMode.EstimatingFacialExpression,
            enable=enable)
        self.conn.send_msg(msg)

    def enable_device_imu(self, enable_raw=False, enable_user=False, enable_gyro=False):
        """Enable streaming of the connected Mobile devices' IMU data.

        The accelerometer and gyro data for the connected phone or tablet can
        be streamed from the app to the SDK. You can request any combination of
        the 3 data types.

        Args:
            enable_raw (bool): True to enable streaming of the raw accelerometer
                data, which can be accessed via :attr:`device_accel_raw`
            enable_user (bool): True to enable streaming of the user-filtered
                accelerometer data, which can be accessed via :attr:`device_accel_user`
            enable_gyro (bool): True to enable streaming of the gyro
                data, which can be accessed via :attr:`device_gyro`
        """
        msg = _clad_to_engine_iface.EnableDeviceIMUData(enableAccelerometerRaw=enable_raw,
                                                        enableAccelerometerUser=enable_user,
                                                        enableGyro=enable_gyro)
        self.conn.send_msg(msg)

    def set_needs_levels(self, repair_value=1, energy_value=1, play_value=1):
        """Manually set Cozmo's current needs levels.

        The needs levels control whether Cozmo needs repairing, feeding or playing with.
        Values outside of the 0.0 to 1.0 range are clamped internally.

        Args:
            repair_value (float): How repaired is Cozmo - 0='broken', 1='fully repaired'
            energy_value (float): How energetic is Cozmo - 0='no-energy', 1='full energy'
            play_value (float): How in need of play is Cozmo - 0='bored', 1='happy'
        """
        msg = _clad_to_engine_iface.ForceSetNeedsLevels(
            newNeedLevel = [repair_value, energy_value, play_value])
        self.conn.send_msg(msg)

    ### Camera Commands ###

    def enable_auto_exposure(self):
        '''
        .. deprecated:: 0.12.0
           Use: :meth:`cozmo.camera.Camera.enable_auto_exposure` instead.
        '''
        warnings.warn("The 'robot.enable_auto_exposure' method is deprecated, "
                      "use 'robot.camera.enable_auto_exposure' instead.", DeprecationWarning, stacklevel=2)
        self.camera.enable_auto_exposure()

    def set_manual_exposure(self, exposure_ms, gain):
        '''
        .. deprecated:: 0.12.0
           Use: :meth:`cozmo.camera.Camera.set_manual_exposure` instead.
        '''
        warnings.warn("The 'robot.set_manual_exposure' method is deprecated, "
                      "use 'robot.camera.set_manual_exposure' instead.", DeprecationWarning, stacklevel=2)
        self.camera.set_manual_exposure(exposure_ms, gain)

    ### Low-Level Commands ###

    def drive_wheel_motors(self, l_wheel_speed, r_wheel_speed,
                                 l_wheel_acc=None, r_wheel_acc=None):
        '''Tell Cozmo to move his wheels / treads at a given speed.

        The wheels will continue to move at that speed until commanded to drive
        at a new speed, or if :meth:`~cozmo.robot.Robot.stop_all_motors` is called.

        Args:
            l_wheel_speed (float): Speed of the left tread (in millimeters per second)
            r_wheel_speed (float): Speed of the right tread (in millimeters per second)
            l_wheel_acc (float): Acceleration of left tread (in millimeters per second squared)
                ``None`` value defaults this to the same as l_wheel_speed.
            r_wheel_acc (float): Acceleration of right tread (in millimeters per second squared)
                ``None`` value defaults this to the same as r_wheel_speed.
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

    async def drive_wheels(self, l_wheel_speed, r_wheel_speed,
                                 l_wheel_acc=None, r_wheel_acc=None, duration=None):
        '''Tell Cozmo to move his wheels / treads at a given speed, and optionally stop them after a given duration.

        If duration is ``None`` then this is equivalent to the non-async
        :meth:`~cozmo.robot.Robot.drive_wheel_motors` method.

        Args:
            l_wheel_speed (float): Speed of the left tread (in millimeters per second).
            r_wheel_speed (float): Speed of the right tread (in millimeters per second).
            l_wheel_acc (float): Acceleration of left tread (in millimeters per second squared).
                ``None`` value defaults this to the same as l_wheel_speed.
            r_wheel_acc (float): Acceleration of right tread (in millimeters per second squared).
                ``None`` value defaults this to the same as r_wheel_speed.
            duration (float): Time for the robot to drive. Will call :meth:`~cozmo.robot.Robot.stop_all_motors`
                after this duration has passed.
        '''
        self.drive_wheel_motors(l_wheel_speed, r_wheel_speed, l_wheel_acc, r_wheel_acc)
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

    def say_text(self, text, play_excited_animation=False, use_cozmo_voice=True,
                 duration_scalar=1.0, voice_pitch=0.0, in_parallel=False, num_retries=0):
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
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.SayText` action object which can be
                queried to see when it is complete
        '''

        action = self.say_text_factory(text=text, play_excited_animation=play_excited_animation,
                                       use_cozmo_voice=use_cozmo_voice, duration_scalar=duration_scalar,
                                       voice_pitch=voice_pitch, conn=self.conn,
                                       robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def set_backpack_lights(self, light1, light2, light3, light4, light5):
        '''Set the lights on Cozmo's backpack.

        The light descriptions below are all from Cozmo's perspective.

        Note: The left and right lights only contain red LEDs, so e.g. setting
        them to green will look off, and setting them to white will look red

        Args:
            light1 (:class:`cozmo.lights.Light`): The left backpack light
            light2 (:class:`cozmo.lights.Light`): The front backpack light
            light3 (:class:`cozmo.lights.Light`): The center backpack light
            light4 (:class:`cozmo.lights.Light`): The rear backpack light
            light5 (:class:`cozmo.lights.Light`): The right backpack light
        '''
        msg = _clad_to_engine_iface.SetBackpackLEDs()
        for i, light in enumerate( (light1, light2, light3, light4, light5) ):
            if light is not None:
                lights._set_light(msg, i, light)

        self.conn.send_msg(msg)

    def set_center_backpack_lights(self, light):
        '''Set the lights in the center of Cozmo's backpack to the same color.

        Forces the lights on the left and right to off (this is useful as those
        lights only support shades of red, so cannot generally be set to the
        same color as the center lights).

        Args:
            light (:class:`cozmo.lights.Light`): The lights for Cozmo's backpack.
        '''
        light_arr = [ light ] * 5
        light_arr[0] = lights.off_light
        light_arr[4] = lights.off_light
        self.set_backpack_lights(*light_arr)

    def set_all_backpack_lights(self, light):
        '''Set the lights on Cozmo's backpack to the same color.

        Args:
            light (:class:`cozmo.lights.Light`): The lights for Cozmo's backpack.
        '''
        light_arr = [ light ] * 5
        self.set_backpack_lights(*light_arr)

    def set_backpack_lights_off(self):
        '''Set the lights on Cozmo's backpack to off.'''
        light_arr = [ lights.off_light ] * 5
        self.set_backpack_lights(*light_arr)

    def set_head_light(self, enable):
        '''Turn Cozmo's IR headlight on or off.

        The headlight is on the front of Cozmo's chassis, between his two
        front wheels, underneath his head. Cozmo's camera is IR sensitive
        so although you cannot see the IR light with the naked eye you will
        see it in Cozmo's camera feed.

        Args:
            enable (bool): True turns the light on, False turns it off.
        '''
        msg = _clad_to_engine_iface.SetHeadlight(enable=enable)
        self.conn.send_msg(msg)

    def enable_freeplay_cube_lights(self, enable=True):
        """Enable, or disable, the automatic cube light mode used in freeplay.

        Enabling the freeplay cube light mode causes the cubes to automatically
        pulse blue when Cozmo can see them - as seen in the Cozmo app during
        freeplay mode. This is disabled by default in SDK mode because it
        overrides any other calls to set the cube light colors.

        Args:
            enable (bool): True to enable the freeplay cube light mode,
                False to disable it.
        """
        if enable:
            self._set_cube_light_state(True)
            self._enable_cube_sleep(False, False)
        else:
            self._enable_cube_sleep(True, True)
            self._set_cube_light_state(False)

    def set_head_angle(self, angle, accel=10.0, max_speed=10.0, duration=0.0,
                       warn_on_clamp=True, in_parallel=False, num_retries=0):
        '''Tell Cozmo's head to turn to a given angle.

        Args:
            angle: (:class:`cozmo.util.Angle`): Desired angle for
                Cozmo's head. (:const:`MIN_HEAD_ANGLE` to
                :const:`MAX_HEAD_ANGLE`).
            accel (float): Acceleration of Cozmo's head in radians per second squared.
            max_speed (float): Maximum speed of Cozmo's head in radians per second.
            duration (float): Time for Cozmo's head to turn in seconds. A value
                of zero will make Cozmo try to do it as quickly as possible.
            warn_on_clamp (bool): True to log a warning if the angle had to be
                clamped to the valid range (:const:`MIN_HEAD_ANGLE` to
                :const:`MAX_HEAD_ANGLE`).
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.SetHeadAngle` action object which can be
                queried to see when it is complete
        '''
        action = self.set_head_angle_factory(angle=angle, max_speed=max_speed,
                accel=accel, duration=duration, warn_on_clamp=warn_on_clamp,
                conn=self.conn, robot=self, dispatch_parent=self)

        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def set_lift_height(self, height, accel=10.0, max_speed=10.0, duration=0.0,
                        in_parallel=False, num_retries=0):
        '''Tell Cozmo's lift to move to a given height

        Args:
            height (float): desired height for Cozmo's lift 0.0 (bottom) to
                1.0 (top) (we clamp it to this range internally).
            accel (float): Acceleration of Cozmo's lift in radians per
                second squared.
            max_speed (float): Maximum speed of Cozmo's lift in radians per second.
            duration (float): Time for Cozmo's lift to move in seconds. A value
                of zero will make Cozmo try to do it as quickly as possible.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.SetLiftHeight` action object which can be
                queried to see when it is complete.
        '''
        action = self.set_lift_height_factory(height=height, max_speed=max_speed,
                accel=accel, duration=duration, conn=self.conn,
                robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action


    ## Animation Commands ##

    def play_audio(self, audio_event):
        '''Sends an audio event to the engine

        Most of these come in pairs, with one to start an audio effect, and one to stop
        if desired.

        Example: 
            :attr:`cozmo.audio.AudioEvents.SfxSharedSuccess` starts a sound
            :attr:`cozmo.audio.AudioEvents.SfxSharedSuccessStop` interrupts that sound in progress

        Some events are part of the TinyOrchestra system which have special behavior.  
        This system can be intitialized and stopped, and various musical instruments can be 
        turned on and off while it is running.

        Args:
            audio_event (object): An attribute of the :class:`cozmo.audio.AudioEvents` class
        '''
        audio_event_id = audio_event.id
        game_object_id = _clad_to_engine_anki.AudioMetaData.GameObjectType.CodeLab

        msg = _clad_to_engine_anki.AudioEngine.Multiplexer.PostAudioEvent(
            audioEvent=audio_event_id, gameObject=game_object_id)
        self.conn.send_msg(msg)

    def play_song(self, song_notes, loop_count=1, in_parallel=False, num_retries=0):
        '''Starts playing song on the robot.

        Plays a provided array of SongNotes using a custom animation on the robot.

        Args:
            song_notes (object[]): An array of :class:`cozmo.song.SongNote` classes

        Returns:
            A :class:`cozmo.anim.Animation` action object which can be queried
                to see when it is complete.
        '''

        msg = _clad_to_engine_iface.ReplaceNotesInSong(notes=song_notes)
        self.conn.send_msg(msg)

        song_animation_name = 'cozmo_sings_custom'
        action = self.animation_factory(song_animation_name, loop_count,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def play_anim(self, name, loop_count=1, in_parallel=False, num_retries=0):
        '''Starts an animation playing on a robot.

        Returns an Animation object as soon as the request to play the animation
        has been sent.  Call the wait_for_completed method on the animation
        if you wish to wait for completion (or listen for the
        :class:`cozmo.anim.EvtAnimationCompleted` event).

        Warning: Specific animations may be renamed or removed in future updates of the app.
            If you want your program to work more reliably across all versions
            we recommend using :meth:`play_anim_trigger` instead.

        Args:
            name (str): The name of the animation to play.
            loop_count (int): Number of times to play the animation.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
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
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def play_anim_trigger(self, trigger, loop_count=1, in_parallel=False,
                          num_retries=0, use_lift_safe=False, ignore_body_track=False,
                          ignore_head_track=False, ignore_lift_track=False):
        """Starts an animation trigger playing on a robot.

        As noted in the Triggers class, playing a trigger requests that an
        animation of a certain class starts playing, rather than an exact
        animation name as influenced by the robot's mood, and other factors.

        Args:
            trigger (object): An attribute of the :class:`cozmo.anim.Triggers` class
            loop_count (int): Number of times to play the animation
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
            use_lift_safe (bool): True to automatically ignore the lift track
                if Cozmo is currently carrying an object.
            ignore_body_track (bool): True to ignore the animation track for
                Cozmo's body (i.e. the wheels / treads).
            ignore_head_track (bool): True to ignore the animation track for
                Cozmo's head.
            ignore_lift_track (bool): True to ignore the animation track for
                Cozmo's lift.
        Returns:
            A :class:`cozmo.anim.AnimationTrigger` action object which can be
                queried to see when it is complete
        Raises:
            :class:`ValueError` if supplied an invalid animation trigger.
        """
        if not isinstance(trigger, anim._AnimTrigger):
            raise TypeError("Invalid trigger supplied")

        action = self.animation_trigger_factory(trigger, loop_count, use_lift_safe,
                                                ignore_body_track, ignore_head_track, ignore_lift_track,
                                                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def set_idle_animation(self, anim_trigger):
        '''Set the Idle Animation on Cozmo

        Idle animations keep Cozmo alive inbetween the times other animations play.
        They behave the same as regular animations except that they
        loop forever until another animation is started.

        Args:
            anim_trigger (:class:`cozmo.anim.Triggers`): The animation trigger to set
        Raises:
            :class:`ValueError` if supplied an invalid animation trigger.
        '''
        if not isinstance(anim_trigger, anim._AnimTrigger):
            raise TypeError("Invalid anim_trigger supplied")

        msg = _clad_to_engine_iface.PushIdleAnimation(animTrigger=anim_trigger.id,
                                                      lockName="sdk")
        self.conn.send_msg(msg)
        self._idle_stack_depth += 1


    def clear_idle_animation(self):
        '''Clears any Idle Animation currently playing on Cozmo'''
        msg = _clad_to_engine_iface.RemoveIdleAnimation(lockName="sdk")

        while(self._idle_stack_depth > 0):
            self.conn.send_msg(msg)
            self._idle_stack_depth -= 1

    # Cozmo's Face animation commands

    def display_oled_face_image(self, screen_data, duration_ms,
                                in_parallel=True):
        ''' Display a bitmap image on Cozmo's OLED face screen.

        Args:
            screen_data (:class:`bytes`): a sequence of pixels (8 pixels per
                byte) (from e.g.
                :func:`cozmo.oled_face.convert_pixels_to_screen_data`).
            duration_ms (float): time to keep displaying this image on Cozmo's
                face (clamped to 30 seconds in engine).
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
        Returns:
            A :class:`cozmo.robot.DisplayOledFaceImage` action object which
                can be queried to see when it is complete.
        Raises:
            :class:`cozmo.exceptions.RobotBusy` if another action is already
                running and in_parallel==False
        '''

        # We never want 2 face image actions active at once, so clear current
        # face image action (if one is running)
        if ((self._current_face_image_action is not None) and
                self._current_face_image_action.is_running):
            self._current_face_image_action.abort()

        action = self.display_oled_face_image_factory(screen_data=screen_data,
                                                      duration_ms=duration_ms,
                                                      conn=self.conn, robot=self,
                                                      dispatch_parent=self)
        self._current_face_image_action = action
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=0)
        return action


    ## Behavior Commands ##

    def start_behavior(self, behavior_type):
        '''Starts executing a behavior.

        Call the :meth:`~cozmo.behavior.Behavior.stop` method on the behavior
        object at some point in the future to terminate execution.

        Args:
            behavior_type (:class:`cozmo.behavior._BehaviorType`):  An attribute of
                :class:`cozmo.behavior.BehaviorTypes`.
        Returns:
            :class:`cozmo.behavior.Behavior`
        Raises:
            :class:`TypeError` if an invalid behavior type is supplied.
        '''
        if not isinstance(behavior_type, behavior._BehaviorType):
            raise TypeError('Invalid behavior supplied')

        if self._current_behavior is not None:
            self._current_behavior._set_stopped()

        new_behavior = self.behavior_factory(self, behavior_type,
                                             is_active=True, dispatch_parent=self)
        msg = _clad_to_engine_iface.ExecuteBehaviorByExecutableType(
                behaviorType=behavior_type.id)
        self.conn.send_msg(msg)
        self._current_behavior = new_behavior
        return new_behavior

    async def run_timed_behavior(self, behavior_type, active_time):
        '''Executes a behavior for a set number of seconds.

        This call blocks and stops the behavior after active_time seconds.

        Args:
            behavior_type (:class:`cozmo.behavior._BehaviorType`): An attribute of
                :class:`cozmo.behavior.BehaviorTypes`.
            active_time (float): specifies the maximum time to execute in seconds
        Raises:
            :class:`TypeError` if an invalid behavior type is supplied.
        '''
        b = self.start_behavior(behavior_type)
        try:
            await b.wait_for_completed(timeout=active_time)
        except asyncio.TimeoutError:
            # It didn't complete within the time, stop it
            b.stop()

    def start_freeplay_behaviors(self):
        '''Start running freeplay behaviors on Cozmo

        Puts Cozmo into a freeplay mode where he autonomously drives around
        and does stuff based on his mood and environment.

        You shouldn't attempt to drive Cozmo during this, as it will clash
        with whatever the current behavior is attempting to do.
        '''
        msg = _clad_to_engine_iface.ActivateHighLevelActivity(
            _clad_to_engine_cozmo.HighLevelActivity.Freeplay)
        self.conn.send_msg(msg)

        self._is_behavior_running = True  # The chooser will run them automatically
        self._is_freeplay_mode_active = True

    def stop_freeplay_behaviors(self):
        '''Stop running freeplay behaviors on Cozmo

        Forces Cozmo out of Freeplay mode and stops any currently running
        behaviors and actions.
        '''

        msg = _clad_to_engine_iface.ActivateHighLevelActivity(
            _clad_to_engine_cozmo.HighLevelActivity.Selection)
        self.conn.send_msg(msg)

        self._is_freeplay_mode_active = False
        self._set_none_behavior()
        self.abort_all_actions()

    ## Object Commands ##

    def pickup_object(self, obj, use_pre_dock_pose=True, in_parallel=False,
                      num_retries=0):
        '''Instruct the robot to pick up the supplied object.

        Args:
            obj (:class:`cozmo.objects.ObservableObject`): The target object to
                pick up where ``obj.pickupable`` is True.
            use_pre_dock_pose (bool): whether or not to try to immediately pick
                up an object or first position the robot next to the object.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.PickupObject` action object which can be
                queried to see when it is complete.
        Raises:
            :class:`cozmo.exceptions.RobotBusy` if another action is already
                running and in_parallel==False
            :class:`cozmo.exceptions.NotPickupable` if object type can't be picked up.
        '''
        if not obj.pickupable:
            raise exceptions.NotPickupable('Cannot pickup this type of object')

        # TODO: Check with the World to see if Cozmo is already holding an object.
        logger.info("Sending pickup object request for object=%s", obj)
        action = self.pickup_object_factory(obj=obj, use_pre_dock_pose=use_pre_dock_pose,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def place_on_object(self, obj, use_pre_dock_pose=True, in_parallel=False,
                        num_retries=0):
        '''Asks Cozmo to place the currently held object onto a target object.

        Args:
            obj (:class:`cozmo.objects.ObservableObject`): The target object to
                place current held object on, where obj.place_objects_on_this
                is True.
            use_pre_dock_pose (bool): Whether or not to try to immediately pick
                up an object or first position the robot next to the object.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.PlaceOnObject` action object which can be
                queried to see when it is complete.
        Raises:
            :class:`cozmo.exceptions.RobotBusy` if another action is already
                running and in_parallel==False
            :class:`cozmo.exceptions.CannotPlaceObjectsOnThis` if the object cannot have objects
            placed on it.
        '''
        if not obj.place_objects_on_this:
            raise exceptions.CannotPlaceObjectsOnThis('Cannot place objects on this type of object')

        # TODO: Check with the World to see if Cozmo is already holding an object.
        logger.info("Sending place on object request for target object=%s", obj)
        action = self.place_on_object_factory(obj=obj, use_pre_dock_pose=use_pre_dock_pose,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def place_object_on_ground_here(self, obj, in_parallel=False, num_retries=0):
        '''Ask Cozmo to place the object he is carrying on the ground at the current location.

        Args:
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.PlaceObjectOnGroundHere` action object which
                can be queried to see when it is complete.
        Raises:
            :class:`cozmo.exceptions.RobotBusy` if another action is already
                running and in_parallel==False
        '''
        # TODO: Check whether Cozmo is known to be holding the object in question
        logger.info("Sending place down here request for object=%s", obj)
        action = self.place_object_on_ground_here_factory(obj=obj,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action


    ## Interact with seen Face Commands ##

    def turn_towards_face(self, face, in_parallel=False, num_retries=0):
        '''Tells Cozmo to turn towards this face.

        Args:
            face: (:class:`cozmo.faces.Face`): The face Cozmo will turn towards.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.TurnTowardsFace` action object which can be
                queried to see when it is complete
        '''
        action = self.turn_towards_face_factory(face=face,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action


    ## Robot Driving Commands ##

    def go_to_pose(self, pose, relative_to_robot=False, in_parallel=False,
                   num_retries=0):
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
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.GoToPose` action object which can be queried
                to see when it is complete.
        '''
        if relative_to_robot:
            pose = self.pose.define_pose_relative_this(pose)
        action = self.go_to_pose_factory(pose=pose,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def go_to_object(self, target_object, distance_from_object,
                     in_parallel=False, num_retries=0):
        '''Tells Cozmo to drive to the specified object.

        Args:
            target_object (:class:`cozmo.objects.ObservableObject`): The destination object.
            distance_from_object (:class:`cozmo.util.Distance`): The distance from the
                object to stop. This is the distance between the origins. For instance,
                the distance from the robot's origin (between Cozmo's two front wheels)
                to the cube's origin (at the center of the cube) is ~40mm.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.GoToObject` action object which can be queried
                to see when it is complete.
        '''
        if not isinstance(target_object, objects.ObservableObject):
            raise TypeError("Target must be an observable object")

        action = self.go_to_object_factory(object_id=target_object.object_id,
                                           distance_from_object=distance_from_object,
                                           conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def dock_with_cube(self, target_object, approach_angle=None,
                       alignment_type=robot_alignment.RobotAlignmentTypes.LiftPlate,
                       distance_from_marker=None,
                       in_parallel=False, num_retries=0):
        '''Tells Cozmo to dock with a specified cube object.

        Args:
            target_object (:class:`cozmo.objects.LightCube`): The cube to dock with.
            approach_angle (:class:`cozmo.util.Angle`): The angle to approach the
                cube from.  For example, 180 degrees will cause cozmo to drive 
                past the cube and approach it from behind.
            alignment_type (:class:`cozmo.robot_alignment.RobotAlignmentTypes`):
                which part of the robot to line up with the front of the object.
            distance_from_marker (:class:`cozmo.util.Distance`): distance from 
                the cube marker to stop when using Custom alignment
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.DockWithCube` action object which can be queried
                to see when it is complete.
        '''
        if not isinstance(target_object, objects.LightCube):
            raise TypeError("Target must be a light cube")

        action = self.dock_with_cube_factory(obj=target_object, approach_angle=approach_angle,
                                             alignment_type=alignment_type, distance_from_marker=distance_from_marker,
                                             conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def roll_cube(self, target_object, approach_angle=None, check_for_object_on_top=False,
                  in_parallel=False, num_retries=0):
        '''Tells Cozmo to roll a specified cube object.

        Args:
            target_object (:class:`cozmo.objects.LightCube`): The cube to roll.
            approach_angle (:class:`cozmo.util.Angle`): The angle to approach the 
                cube from.   For example, 180 degrees will cause cozmo to drive
                past the cube and approach it from behind.
            check_for_object_on_top (bool): If there is a cube on top of the 
                specified cube, and check_for_object_on_top is True, then Cozmo 
                will ignore the action.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.RollCube` action object which can be queried
                to see when it is complete.
        '''
        if not isinstance(target_object, objects.LightCube):
            raise TypeError("Target must be a light cube")

        action = self.roll_cube_factory(obj=target_object, approach_angle=approach_angle,
                                        check_for_object_on_top=check_for_object_on_top,
                                        conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def pop_a_wheelie(self, target_object, approach_angle=None,
                      in_parallel=False, num_retries=0):
        '''Tells Cozmo to "pop a wheelie" using a light cube.

        Args:
            target_object (:class:`cozmo.objects.LightCube`): The cube to push
                down on with cozmo's lift, to start the wheelie.
            approach_angle (:class:`cozmo.util.Angle`): The angle to approach the
                cube from. For example, 180 degrees will cause cozmo to drive
                past the cube and approach it from behind.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
            A :class:`cozmo.robot.PopAWheelie` action object which can be queried
                to see when it is complete.
        '''
        if not isinstance(target_object, objects.LightCube):
            raise TypeError("Target must be a light cube")

        action = self.pop_a_wheelie_factory(obj=target_object,
                                            approach_angle=approach_angle,
                                            conn=self.conn,
                                            robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def turn_in_place(self, angle, in_parallel=False, num_retries=0, speed=None,
                      accel=None, angle_tolerance=None, is_absolute=False):
        '''Turn the robot around its current position.

        Args:
            angle (:class:`cozmo.util.Angle`): The angle to turn. Positive
                values turn to the left, negative values to the right.
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
            speed (:class:`cozmo.util.Angle`): Angular turn speed (per second).
            accel (:class:`cozmo.util.Angle`): Acceleration of angular turn
                (per second squared).
            angle_tolerance (:class:`cozmo.util.Angle`): angular tolerance
                to consider the action complete (this is clamped to a minimum
                of 2 degrees internally).
            is_absolute (bool): True to turn to a specific angle, False to
                turn relative to the current pose.
        Returns:
            A :class:`cozmo.robot.TurnInPlace` action object which can be
                queried to see when it is complete.
        '''
        action = self.turn_in_place_factory(angle=angle, speed=speed,
                accel=accel, angle_tolerance=angle_tolerance, is_absolute=is_absolute,
                conn=self.conn, robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    def drive_off_charger_contacts(self, in_parallel=False, num_retries=0):
        '''Tells Cozmo to drive forward slightly to get off the charger contacts.

        All motor movement is disabled while Cozmo is on the charger to
        prevent hardware damage. This command is the one exception and provides
        a way to drive forward a little to disconnect from the charger contacts
        and thereby re-enable all other commands.

        Args:
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
        Returns:
           A :class:`cozmo.robot.DriveOffChargerContacts` action object which
            can be queried to see when it is complete.
        '''
        action = self.drive_off_charger_contacts_factory(conn=self.conn,
                robot=self, dispatch_parent=self)
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    async def backup_onto_charger(self, max_drive_time=3):
        '''Attempts to reverse robot onto its charger.

        This method assumes the charger is directly behind the robot and
        will keep driving straight back until charger is in contact, or until
        a timeout is reached.

        Args:
            max_drive_time (float): The maximum amount of time in seconds
                to reverse the robot without detecting the charger.
        '''

        await self.drive_wheels(-30, -30)
        timeout = util.Timeout(timeout=max_drive_time)
        while not (timeout.is_timed_out or self.is_on_charger) :
            await asyncio.sleep(0.1, loop=self.loop)

        self.stop_all_motors()

    def perform_off_charger(self):
        '''Returns a context manager to move the robot off of and back onto the charger.

        If the robot is on the charger, it will move a short distance off the contacts,
        perform the code wrapped by the context and then move the robot back onto the
        charger after the wrapped code completes.

        Synchronous example::

            with robot.perform_off_charger():
                action = robot.say_text("Hello")
                action.wait_for_completed()

        Asynchronous example::

            async with robot.perform_off_charger():
                action = robot.say_text("Hello")
                await action.wait_for_completed()
        '''
        return self.perform_off_charger_factory(self)

    def drive_straight(self, distance, speed, should_play_anim=True,
                       in_parallel=False, num_retries=0):
        '''Tells Cozmo to drive in a straight line

        Cozmo will drive for the specified distance (forwards or backwards)

        Args:
            distance (:class:`cozmo.util.Distance`): The distance to drive
                (>0 for forwards, <0 for backwards)
            speed (:class:`cozmo.util.Speed`): The speed to drive at
                (should always be >0, the abs(speed) is used internally)
            should_play_anim (bool): Whether to play idle animations
                whilst driving (tilt head, hum, animated eyes, etc.)
            in_parallel (bool): True to run this action in parallel with
                previous actions, False to require that all previous actions
                be already complete.
            num_retries (int): Number of times to retry the action if the
                previous attempt(s) failed.
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
        self._action_dispatcher._send_single_action(action,
                                                    in_parallel=in_parallel,
                                                    num_retries=num_retries)
        return action

    async def wait_for_all_actions_completed(self):
        '''Waits until all SDK-initiated actions are complete.'''
        await self._action_dispatcher.wait_for_all_actions_completed()


_UnexpectedMovementSide = collections.namedtuple('_UnexpectedMovementSide', ['name', 'id'])

class UnexpectedMovementSide(CladEnumWrapper):
    '''Defines the side of collision that caused unexpected movement.
    
    This will always be UNKNOWN while reaction triggers are disabled.
    Call :meth:`cozmo.robot.Robot.enable_all_reaction_triggers` to enable reaction triggers.
    '''
    _clad_enum = _clad_to_engine_cozmo.UnexpectedMovementSide
    _entry_type = _UnexpectedMovementSide

    #: Unable to tell what side obstructed movement. 
    #: Usually caused by reaction triggers being disabled.
    Unknown = _entry_type("Unknown", _clad_enum.UNKNOWN)

    #: Obstruction detected in front of the robot.
    Front = _entry_type("Front", _clad_enum.FRONT)

    #: Obstruction detected behind the robot.
    Back = _entry_type("Back", _clad_enum.BACK)

    #: Obstruction detected to the left of the robot
    Left = _entry_type("Left", _clad_enum.LEFT)

    #: Obstruction detected to the right of the robot
    Right = _entry_type("Right", _clad_enum.RIGHT)

UnexpectedMovementSide._init_class()


_UnexpectedMovementType = collections.namedtuple('_UnexpectedMovementType', ['name', 'id'])

class UnexpectedMovementType(CladEnumWrapper):
    '''Defines the type of unexpected movement.'''
    _clad_enum = _clad_to_engine_cozmo.UnexpectedMovementType
    _entry_type = _UnexpectedMovementType

    #: Tried to turn, but couldn't.
    TurnedButStopped = _entry_type("TurnedButStopped", _clad_enum.TURNED_BUT_STOPPED)
    
    # Turned in the expected direction, but turned further than expected. 
    # Currently unused.
    _TurnedInSameDirection = _entry_type("TurnedInSameDirection", _clad_enum.TURNED_IN_SAME_DIRECTION)
    
    #: Expected to turn in one direction, but turned the other way. 
    #: Also happens when rotation is unexpected.
    TurnedInOppositeDirection = _entry_type("TurnedInOppositeDirection", _clad_enum.TURNED_IN_OPPOSITE_DIRECTION)

UnexpectedMovementType._init_class()
