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

'''
Behaviors represent a task that Cozmo may perform for an
indefinite amount of time.

For example, the "LookAroundInPlace" behavior causes Cozmo to start looking
around him (without driving), which will cause events such as
:class:`cozmo.objects.EvtObjectObserved` to be generated as he comes across
objects.

Behaviors must be explicitly stopped before having the robot do something else
(for example, pick up the object he just observed).

Behaviors are started by a call to :meth:`cozmo.robot.Robot.start_behavior`,
which returns a :class:`Behavior` object.  Calling the :meth:`~Behavior.stop`
method on that object terminate the behavior.

The :class:`BehaviorTypes` class in this module holds a list of all available
behaviors.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['BEHAVIOR_IDLE', 'BEHAVIOR_REQUESTED', 'BEHAVIOR_RUNNING',
           'BEHAVIOR_STOPPED',
           'EvtBehaviorRequested', 'EvtBehaviorStarted', 'EvtBehaviorStopped',
           'Behavior', 'BehaviorTypes']

import collections

from . import logger
from . import event
from ._clad import _clad_to_engine_cozmo, CladEnumWrapper


#: string: Behavior idle state (not requested to run)
BEHAVIOR_IDLE = 'behavior_idle'

#: string: Behavior requested state (waiting for engine to start it)
BEHAVIOR_REQUESTED = 'behavior_requested'

#: string: Behavior running state
BEHAVIOR_RUNNING = 'behavior_running'

#: string: Behavior stopped state
BEHAVIOR_STOPPED = 'behavior_stopped'


class EvtBehaviorRequested(event.Event):
    '''Triggered when a behavior is requested to start.'''
    behavior = 'The Behavior object'
    behavior_type_name = 'The behavior type name - equivalent to behavior.type.name'


class EvtBehaviorStarted(event.Event):
    '''Triggered when a behavior starts running on the robot.'''
    behavior = 'The Behavior object'
    behavior_type_name = 'The behavior type name - equivalent to behavior.type.name'


class EvtBehaviorStopped(event.Event):
    '''Triggered when a behavior stops.'''
    behavior = 'The behavior type object'
    behavior_type_name = 'The behavior type name - equivalent to behavior.type.name'


class Behavior(event.Dispatcher):
    '''A Behavior instance describes a behavior the robot is currently performing.

    Returned by :meth:`cozmo.robot.Robot.start_behavior`.
    '''

    def __init__(self, robot, behavior_type, is_active=False, **kw):
        super().__init__(**kw)
        self.robot = robot
        self.type = behavior_type
        self._state = BEHAVIOR_IDLE
        if is_active:
            self._state = BEHAVIOR_REQUESTED
            self.dispatch_event(EvtBehaviorRequested, behavior=self, behavior_type_name=self.type.name)

    def __repr__(self):
        return '<%s type="%s">' % (self.__class__.__name__, self.type.name)

    def _on_engine_started(self):
        if self._state != BEHAVIOR_REQUESTED:
            # has not been requested (is an unrelated behavior transition)
            if self.is_running:
                logger.warning("Behavior '%s' unexpectedly reported started when already running")
            return
        self._state = BEHAVIOR_RUNNING
        self.dispatch_event(EvtBehaviorStarted, behavior=self, behavior_type_name=self.type.name)

    def _set_stopped(self):
        if not self.is_active:
            return
        self._state = BEHAVIOR_STOPPED
        self.dispatch_event(EvtBehaviorStopped, behavior=self, behavior_type_name=self.type.name)

    def stop(self):
        '''Requests that the robot stop performing the behavior.

        Has no effect if the behavior is not presently active.
        '''
        if not self.is_active:
            return
        self.robot._set_none_behavior()
        self._set_stopped()

    @property
    def is_active(self):
        '''bool: True if the behavior is currently active and may run on the robot.'''
        return self._state == BEHAVIOR_REQUESTED or self._state == BEHAVIOR_RUNNING

    @property
    def is_running(self):
        '''bool: True if the behavior is currently running on the robot.'''
        return self._state == BEHAVIOR_RUNNING

    @property
    def is_completed(self):
        return self._state == BEHAVIOR_STOPPED

    async def wait_for_started(self, timeout=5):
        '''Waits for the behavior to start.

        Args:
            timeout (int or None): Maximum time in seconds to wait for the event.
                Pass None to wait indefinitely. If a behavior can run it should
                usually start within ~0.2 seconds.
        Raises:
            :class:`asyncio.TimeoutError`
        '''
        if self.is_running or self.is_completed:
            # Already started running
            return
        await self.wait_for(EvtBehaviorStarted, timeout=timeout)

    async def wait_for_completed(self, timeout=None):
        '''Waits for the behavior to complete.

        Args:
            timeout (int or None): Maximum time in seconds to wait for the event.
                Pass None to wait indefinitely.
        Raises:
            :class:`asyncio.TimeoutError`
        '''
        if self.is_completed:
            # Already complete
            return
        # Wait for behavior to start first - it can't complete without starting,
        # and if it doesn't start within a fraction of a second it probably
        # never will
        await self.wait_for_started()
        await self.wait_for(EvtBehaviorStopped, timeout=timeout)


_BehaviorType = collections.namedtuple('_BehaviorType', ['name', 'id'])


class BehaviorTypes(CladEnumWrapper):
    '''Defines all executable robot behaviors.

    For use with :meth:`cozmo.robot.Robot.start_behavior`.
    '''
    _clad_enum = _clad_to_engine_cozmo.ExecutableBehaviorType
    _entry_type = _BehaviorType

    #: Turn and move head, but don't drive, with Cozmo's head angled
    #: upwards where faces are likely to be.
    FindFaces = _entry_type("FindFaces", _clad_enum.FindFaces)

    #: Knock over a stack of cubes.
    KnockOverCubes = _entry_type("KnockOverCubes", _clad_enum.KnockOverCubes)

    #: Turn and move head, but don't drive, to see what is around Cozmo.
    LookAroundInPlace = _entry_type("LookAroundInPlace", _clad_enum.LookAroundInPlace)

    #: Tries to "pounce" (drive forward and lower lift) when it detects
    #: nearby motion on the ground plane.
    PounceOnMotion = _entry_type("PounceOnMotion", _clad_enum.PounceOnMotion)

    #: Roll a block, regardless of orientation.
    RollBlock = _entry_type("RollBlock", _clad_enum.RollBlock)

    #: Pickup one block, and stack it onto another block.
    StackBlocks = _entry_type("StackBlocks", _clad_enum.StackBlocks)

    # Enroll a Face - for internal use by Face.name_face (requires additional pre/post setup)
    _EnrollFace = _entry_type("EnrollFace", _clad_enum.EnrollFace)


# This enum deliberately only exposes a sub-set of working behaviors
BehaviorTypes._init_class(warn_on_missing_definitions=False, add_missing_definitions=False)
