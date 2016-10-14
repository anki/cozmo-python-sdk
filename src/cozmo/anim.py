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
Animation related classes, functions, events and values.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['EvtAnimationsLoaded', 'EvtAnimationCompleted',
           'Animation', 'AnimationTrigger', 'AnimationNames', 'Triggers',
           'animation_completed_filter']

import collections

from . import logger

from . import action
from . import exceptions
from . import event

from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo


class EvtAnimationsLoaded(event.Event):
    '''Triggered when animations names have been received from the engine'''


class EvtAnimationCompleted(action.EvtActionCompleted):
    '''Triggered when an animation completes.'''
    animation_name = "The name of the animation or trigger that completed"


class Animation(action.Action):
    '''An Animation describes an actively-playing animation on a robot.'''

    _action_type = _clad_to_engine_cozmo.RobotActionType.PLAY_ANIMATION

    def __init__(self, anim_name, loop_count, **kw):
        super().__init__(**kw)

        #: The name of the animation that was dispatched
        self.anim_name = anim_name

        #: The number of iterations the animation was requested for
        self.loop_count = loop_count

    def _repr_values(self):
        return "anim_name=%s loop_count=%s" % (self.anim_name, self.loop_count)

    def _encode(self):
        return _clad_to_engine_iface.PlayAnimation(
            robotID=self.robot.robot_id, animationName=self.anim_name, numLoops=self.loop_count)


class AnimationTrigger(action.Action):
    '''An AnimationTrigger represents a playing animation trigger.

    Asking Cozmo to play an AnimationTrigger causes him to pick one of the
    animations represented by the group.
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.PLAY_ANIMATION

    def __init__(self, trigger, loop_count, **kw):
        super().__init__(**kw)

        #: The trigger that was dispatched
        self.trigger = trigger

        #: The number of iterations the animation was requested for
        self.loop_count = loop_count

    def _repr_values(self):
        return "trigger=%s loop_count=%s" % (self.trigger.name, self.loop_count)

    def _encode(self):
        return _clad_to_engine_iface.PlayAnimationTrigger(
            robotID=self.robot.robot_id, trigger=self.trigger.id, numLoops=self.loop_count)

    def _dispatch_completed_event(self, msg):
        self.dispatch_event(EvtAnimationCompleted,
                action=self, state=self._state,
                animation_name=self.trigger.name)



class AnimationNames(event.Dispatcher, set):
    '''Holds the set of animation names (strings) returned from the Engine.

    Animation names are dynamically retrieved from the engine when the SDK
    connects to it, unlike :class:`Triggers` which are defined at runtime.
    '''
    def __init__(self, conn, **kw):
        super().__init__(self, **kw)
        self._conn = conn
        self._loaded = False

    def __contains__(self, key):
        if not self._loaded:
            raise exceptions.AnimationsNotLoaded("Animations not yet received from engine")
        return super().__contains__(key)

    def __hash__(self):
        # We want to compare AnimationName instances rather than the
        # names they contain
        return id(self)

    def refresh(self):
        '''Causes the list of animation names to be re-requested from the engine.

        Attempting to play an animation while the list is refreshing will result
        in an AnimationsNotLoaded exception being raised.

        Generates an EvtAnimationsLoaded event once completed.
        '''
        self._loaded = False
        self.clear()
        self._conn.send_msg(_clad_to_engine_iface.RequestAvailableAnimations())

    @property
    def is_loaded(self):
        '''bool: True if the animation names have been received from the engine.'''
        return self._loaded != False

    async def wait_for_loaded(self, timeout=None):
        '''Wait for the animation names to be loaded from the engine.

        Returns:
                The :class:`EvtAnimationsLoaded` instance once loaded
        Raises:
            :class:`asyncio.TimeoutError`
        '''
        if self._loaded:
            return self._loaded
        return await self.wait_for(EvtAnimationsLoaded, timeout=timeout)

    def _recv_msg_animation_available(self, evt, msg):
        name = msg.animName
        self.add(name)

    def _recv_msg_end_of_message(self, evt, msg):
        if not self._loaded:
            logger.info("%d animations loaded", len(self))
            self._loaded = evt
            self.dispatch_event(EvtAnimationsLoaded)


# generate names for each CLAD defined trigger

_AnimTrigger = collections.namedtuple('_AnimTrigger', 'name id')
class Triggers:
    """Playing an animation trigger causes the game engine play an animation of a particular type.

    The engine may pick one of a number of actual animations to play based on
    Cozmo's mood or emotion, or with random weighting.  Thus playing the same
    trigger twice may not result in the exact same underlying animation playing
    twice.

    To play an exact animation, use play_anim with a named animation.

    This class holds the set of defined animations triggers to pass to play_anim_trigger.
    """

for (_name, _id) in _clad_to_engine_cozmo.AnimationTrigger.__dict__.items():
    if not _name.startswith('_'):
        setattr(Triggers, _name, _AnimTrigger(_name, _id))


def animation_completed_filter():
    '''Creates an :class:`como.event.Filter` to wait specifically for an animation completed event.'''
    return event.Filter(action.EvtActionCompleted,
        action=lambda action: isinstance(action, Animation))
