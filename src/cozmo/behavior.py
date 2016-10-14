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
__all__ = ['EvtBehaviorStarted', 'EvtBehaviorStopped',
           'Behavior', 'BehaviorTypes']

import asyncio
import collections

from .version import __cozmoclad_version__
from . import logger
from . import event
from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo


class EvtBehaviorStarted(event.Event):
    '''Triggered when a behavior starts.'''
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
        self._is_active = is_active
        if is_active:
            self.dispatch_event(EvtBehaviorStarted, behavior=self, behavior_type_name=self.type.name)

    def __repr__(self):
        return '<%s type="%s">' % (self.__class__.__name__, self.type.name)

    def stop(self):
        '''Requests that the robot stop performing the behavior.

        Has no effect if the behavior is not presently active.
        '''
        if not self._is_active:
            return
        msg = _clad_to_engine_iface.ExecuteBehaviorByExecutableType(
                behaviorType=_clad_to_engine_cozmo.ExecutableBehaviorType.NoneBehavior)
        self.robot.conn.send_msg(msg)
        self._is_active = False
        self.dispatch_event(EvtBehaviorStopped, behavior=self, behavior_type_name=self.type.name)

    @property
    def is_active(self):
        '''bool: True if the behavior is currently active on the robot.'''
        return self._is_active



_BehaviorType = collections.namedtuple('_BehaviorType', ['name', 'id'])

try:
    class BehaviorTypes:
        '''Defines all executable robot behaviors.

        For use with :meth:`cozmo.robot.Robot.start_behavior`.
        '''

        #: Turn and move head, but don't drive, with Cozmo's head angled
        #: upwards where faces are likely to be.
        FindFaces = _BehaviorType("FindFaces", _clad_to_engine_cozmo.ExecutableBehaviorType.FindFaces)

        #: Knock over a stack of cubes.
        KnockOverCubes = _BehaviorType("KnockOverCubes", _clad_to_engine_cozmo.ExecutableBehaviorType.KnockOverCubes)

        #: Turn and move head, but don't drive, to see what is around Cozmo.
        LookAroundInPlace = _BehaviorType("LookAroundInPlace", _clad_to_engine_cozmo.ExecutableBehaviorType.LookAroundInPlace)

        #: Tries to "pounce" (drive forward and lower lift) when it detects
        #: nearby motion on the ground plane.
        PounceOnMotion = _BehaviorType("PounceOnMotion", _clad_to_engine_cozmo.ExecutableBehaviorType.PounceOnMotion)

        #: Roll a block, regardless of orientation.
        RollBlock = _BehaviorType("RollBlock", _clad_to_engine_cozmo.ExecutableBehaviorType.RollBlock)

        #: Pickup one block, and stack it onto another block.
        StackBlocks = _BehaviorType("StackBlocks", _clad_to_engine_cozmo.ExecutableBehaviorType.StackBlocks)

except AttributeError as exc:
    err = ('Incorrect version of cozmoclad package installed.  '
            'run "pip install --ignore-installed cozmoclad==%s" '
            '(error: %s in behavior.py)' % (__cozmoclad_version__, exc))
    raise ImportError(err) from exc

