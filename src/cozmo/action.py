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

'''
Actions encapsulate specific high-level tasks that the Cozmo robot can perform.
They have a definite beginning and end.

These tasks include picking up an object, rotating in place, saying text, etc.

Actions are usually triggered by a call to a method on the
:class:`cozmo.robot.Robot` class such as :meth:`~cozmo.robot.Robot.turn_in_place`

The call will return an object that subclasses :class:`Action` that can be
used to cancel the action, or be observed to wait or be notified when the
action completes (or fails) by calling its
:meth:`~cozmo.event.Dispatcher.wait_for` or
:meth:`~cozmo.event.Dispatcher.add_event_handler` methods.


Warning:
    Unless you pass ``in_parallel=True`` when starting the action, no other
    action can be active at the same time.  Attempting to trigger a non-parallel
    action when another action is already in progress will result in a
    :class:`~cozmo.exceptions.RobotBusy` exception being raised.

    When using ``in_parallel=True`` you may see an action fail with the result
    :attr:`ActionResults.TRACKS_LOCKED` - this indicates that another in-progress
    action has already locked that movement track (e.g. two actions cannot
    move the head at the same time).
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['ACTION_IDLE', 'ACTION_RUNNING', 'ACTION_SUCCEEDED',
           'ACTION_FAILED', 'ACTION_ABORTING',
           'EvtActionStarted', 'EvtActionCompleted', 'Action', 'ActionResults']


from collections import namedtuple
import sys

from . import logger

from . import event
from . import exceptions
from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo, _clad_to_game_cozmo, CladEnumWrapper


#: string: Action idle state
ACTION_IDLE = 'action_idle'

#: string: Action running state
ACTION_RUNNING = 'action_running'

#: string: Action succeeded state
ACTION_SUCCEEDED = 'action_succeeded'

#: string: Action failed state
ACTION_FAILED = 'action_failed'

#: string: Action failed state
ACTION_ABORTING = 'action_aborting'

_VALID_STATES = {ACTION_IDLE, ACTION_RUNNING, ACTION_SUCCEEDED, ACTION_FAILED, ACTION_ABORTING}


class _ActionResult(namedtuple('_ActionResult', 'name id')):
    # Tuple mapping between CLAD ActionResult name and ID
    # All instances will be members of ActionResults

    # Keep _ActionResult as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'ActionResults.%s' % self.name


class ActionResults(CladEnumWrapper):
    """The possible result values for an Action.

    An Action's result is set when the action completes.
    """
    _clad_enum = _clad_to_game_cozmo.ActionResult
    _entry_type = _ActionResult

    #: Action completed successfully.
    SUCCESS = _ActionResult("SUCCESS", _clad_enum.SUCCESS)

    #: Action is still running.
    RUNNING = _ActionResult("RUNNING", _clad_enum.RUNNING)

    #: Action was cancelled (e.g. via :meth:`~cozmo.robot.Robot.abort_all_actions` or
    #: :meth:`Action.abort`).
    CANCELLED_WHILE_RUNNING = _ActionResult("CANCELLED_WHILE_RUNNING", _clad_enum.CANCELLED_WHILE_RUNNING)

    #: Action aborted itself (e.g. had invalid attributes, or a runtime failure).
    ABORT = _ActionResult("ABORT", _clad_enum.ABORT)

    #: Animation Action aborted itself (e.g. there was an error playing the animation).
    ANIM_ABORTED = _ActionResult("ANIM_ABORTED", _clad_enum.ANIM_ABORTED)

    #: There was an error related to vision markers.
    BAD_MARKER = _ActionResult("BAD_MARKER", _clad_enum.BAD_MARKER)

    # (Undocumented) There was a problem related to a subscribed or unsupported message tag (indicates bug in engine)
    BAD_MESSAGE_TAG = _ActionResult("BAD_MESSAGE_TAG", _clad_enum.BAD_MESSAGE_TAG)

    #: There was a problem with the Object ID provided (e.g. there is no Object with that ID).
    BAD_OBJECT = _ActionResult("BAD_OBJECT", _clad_enum.BAD_OBJECT)

    #: There was a problem with the Pose provided.
    BAD_POSE = _ActionResult("BAD_POSE", _clad_enum.BAD_POSE)

    # (Undocumented) The SDK-provided tag was bad (shouldn't occur - would indicate a bug in the SDK)
    BAD_TAG = _ActionResult("BAD_TAG", _clad_enum.BAD_TAG)

    # (Undocumented) Shouldn't occur outside of factory
    FAILED_SETTING_CALIBRATION = _ActionResult("FAILED_SETTING_CALIBRATION", _clad_enum.FAILED_SETTING_CALIBRATION)

    #: There was an error following the planned path.
    FOLLOWING_PATH_BUT_NOT_TRAVERSING = _ActionResult("FOLLOWING_PATH_BUT_NOT_TRAVERSING", _clad_enum.FOLLOWING_PATH_BUT_NOT_TRAVERSING)

    #: The action was interrupted by another Action or Behavior.
    INTERRUPTED = _ActionResult("INTERRUPTED", _clad_enum.INTERRUPTED)

    #: The robot ended up in an "off treads state" not valid for this action (e.g.
    #: the robot was placed on its back while executing a turn)
    INVALID_OFF_TREADS_STATE = _ActionResult("INVALID_OFF_TREADS_STATE",
                                             _clad_to_game_cozmo.ActionResult.INVALID_OFF_TREADS_STATE)

    #: The Up Axis of a carried object doesn't match the desired placement pose.
    MISMATCHED_UP_AXIS = _ActionResult("MISMATCHED_UP_AXIS", _clad_enum.MISMATCHED_UP_AXIS)

    #: No valid Animation name was found.
    NO_ANIM_NAME = _ActionResult("NO_ANIM_NAME", _clad_enum.NO_ANIM_NAME)

    #: An invalid distance value was given.
    NO_DISTANCE_SET = _ActionResult("NO_DISTANCE_SET", _clad_enum.NO_DISTANCE_SET)

    #: There was a problem with the Face ID (e.g. Cozmo doesn't no where it is).
    NO_FACE = _ActionResult("NO_FACE", _clad_enum.NO_FACE)

    #: No goal pose was set.
    NO_GOAL_SET = _ActionResult("NO_GOAL_SET", _clad_enum.NO_GOAL_SET)

    #: No pre-action poses were found (e.g. could not get into position).
    NO_PREACTION_POSES = _ActionResult("NO_PREACTION_POSES", _clad_enum.NO_PREACTION_POSES)

    #: No object is being carried, but the action requires one.
    NOT_CARRYING_OBJECT_ABORT = _ActionResult("NOT_CARRYING_OBJECT_ABORT", _clad_enum.NOT_CARRYING_OBJECT_ABORT)

    #: Initial state of an Action to indicate it has not yet started.
    NOT_STARTED = _ActionResult("NOT_STARTED", _clad_enum.NOT_STARTED)

    #: No sub-action was provided.
    NULL_SUBACTION = _ActionResult("NULL_SUBACTION", _clad_enum.NULL_SUBACTION)

    #: Cozmo was unable to plan a path.
    PATH_PLANNING_FAILED_ABORT = _ActionResult("PATH_PLANNING_FAILED_ABORT", _clad_enum.PATH_PLANNING_FAILED_ABORT)

    #: The object that Cozmo is attempting to pickup is unexpectedly moving (e.g
    #: it is being moved by someone else).
    PICKUP_OBJECT_UNEXPECTEDLY_MOVING = _ActionResult("PICKUP_OBJECT_UNEXPECTEDLY_MOVING", _clad_enum.PICKUP_OBJECT_UNEXPECTEDLY_MOVING)

    #: The object that Cozmo thought he was lifting didn't start moving, so he
    #: must have missed.
    PICKUP_OBJECT_UNEXPECTEDLY_NOT_MOVING = _ActionResult("PICKUP_OBJECT_UNEXPECTEDLY_NOT_MOVING", _clad_enum.PICKUP_OBJECT_UNEXPECTEDLY_NOT_MOVING)

    # (Undocumented) Shouldn't occur in SDK usage
    SEND_MESSAGE_TO_ROBOT_FAILED = _ActionResult("SEND_MESSAGE_TO_ROBOT_FAILED", _clad_enum.SEND_MESSAGE_TO_ROBOT_FAILED)

    #: Cozmo is unexpectedly still carrying an object.
    STILL_CARRYING_OBJECT = _ActionResult("STILL_CARRYING_OBJECT", _clad_enum.STILL_CARRYING_OBJECT)

    #: The Action timed out before completing correctly.
    TIMEOUT = _ActionResult("TIMEOUT", _clad_enum.TIMEOUT)

    #: One or more animation tracks (Head, Lift, Body, Face, Backpack Lights, Audio)
    #: are already being used by another Action.
    TRACKS_LOCKED = _ActionResult("TRACKS_LOCKED", _clad_enum.TRACKS_LOCKED)

    #: There was an internal error related to an unexpected type of dock action.
    UNEXPECTED_DOCK_ACTION = _ActionResult("UNEXPECTED_DOCK_ACTION", _clad_enum.UNEXPECTED_DOCK_ACTION)

    # (Undocumented) Shouldn't occur outside of factory.
    UNKNOWN_TOOL_CODE = _ActionResult("UNKNOWN_TOOL_CODE", _clad_enum.UNKNOWN_TOOL_CODE)

    # (Undocumented) There was a problem in the subclass's update.
    UPDATE_DERIVED_FAILED = _ActionResult("UPDATE_DERIVED_FAILED", _clad_enum.UPDATE_DERIVED_FAILED)

    #: Cozmo did not see the expected result (e.g. unable to see cubes in their
    #: expected position after a related action).
    VISUAL_OBSERVATION_FAILED = _ActionResult("VISUAL_OBSERVATION_FAILED", _clad_enum.VISUAL_OBSERVATION_FAILED)

    #: The Action failed, but may succeed if retried.
    RETRY = _ActionResult("RETRY", _clad_enum.RETRY)

    #: Failed to get into position.
    DID_NOT_REACH_PREACTION_POSE = _ActionResult("DID_NOT_REACH_PREACTION_POSE", _clad_enum.DID_NOT_REACH_PREACTION_POSE)

    #: Failed to follow the planned path.
    FAILED_TRAVERSING_PATH = _ActionResult("FAILED_TRAVERSING_PATH", _clad_enum.FAILED_TRAVERSING_PATH)

    #: The previous attempt to pick and place an object failed.
    LAST_PICK_AND_PLACE_FAILED = _ActionResult("LAST_PICK_AND_PLACE_FAILED", _clad_enum.LAST_PICK_AND_PLACE_FAILED)

    #: The required motor isn't moving so the action cannot complete.
    MOTOR_STOPPED_MAKING_PROGRESS = _ActionResult("MOTOR_STOPPED_MAKING_PROGRESS", _clad_enum.MOTOR_STOPPED_MAKING_PROGRESS)

    #: Not carrying an object when it was expected, but may succeed if the action is retried.
    NOT_CARRYING_OBJECT_RETRY = _ActionResult("NOT_CARRYING_OBJECT_RETRY", _clad_enum.NOT_CARRYING_OBJECT_RETRY)
    
    #: Cozmo is expected to be on the charger, but is not.
    NOT_ON_CHARGER = _ActionResult("NOT_ON_CHARGER", _clad_enum.NOT_ON_CHARGER)

    #: Cozmo was unable to plan a path, but may succeed if the action is retried.
    PATH_PLANNING_FAILED_RETRY = _ActionResult("PATH_PLANNING_FAILED_RETRY", _clad_enum.PATH_PLANNING_FAILED_RETRY)

    #: There is no room to place the object at the desired destination.
    PLACEMENT_GOAL_NOT_FREE = _ActionResult("PLACEMENT_GOAL_NOT_FREE", _clad_enum.PLACEMENT_GOAL_NOT_FREE)

    #: Cozmo failed to drive off the charger.
    STILL_ON_CHARGER = _ActionResult("STILL_ON_CHARGER", _clad_enum.STILL_ON_CHARGER)

    #: Cozmo's pitch is at an unexpected angle for the Action.
    UNEXPECTED_PITCH_ANGLE = _ActionResult("UNEXPECTED_PITCH_ANGLE", _clad_enum.UNEXPECTED_PITCH_ANGLE)


ActionResults._init_class()


class EvtActionStarted(event.Event):
    '''Triggered when a robot starts an action.'''
    action = "The action that started"


class EvtActionCompleted(event.Event):
    '''Triggered when a robot action has completed or failed.'''
    action = "The action that completed"
    state = 'The state of the action; either cozmo.action.ACTION_SUCCEEDED or cozmo.action.ACTION_FAILED'
    failure_code = 'A failure code such as "cancelled"'
    failure_reason = 'A human-readable failure reason'


class Action(event.Dispatcher):
    """An action holds the state of an in-progress robot action
    """
    # We allow sub-classes of Action to optionally disable logging messages
    # related to those actions being aborted - this is useful for actions
    # that are aborted frequently (by design) and would otherwise spam the log
    _enable_abort_logging = True

    def __init__(self, *, conn, robot, **kw):
        super().__init__(**kw)
        #: :class:`~cozmo.conn.CozmoConnection`: The connection on which the action was sent.
        self.conn = conn

        #: :class:`~cozmo.robot.Robot`: Th robot instance executing the action.
        self.robot = robot

        self._action_id = None
        self._state = ACTION_IDLE
        self._failure_code = None
        self._failure_reason = None
        self._result = None
        self._completed_event = None
        self._completed_event_pending = False

    def __repr__(self):
        extra = self._repr_values()
        if len(extra) > 0:
            extra = ' '+extra
        if self._state == ACTION_FAILED:
            extra += (" failure_reason='%s' failure_code=%s result=%s" %
                      (self._failure_reason, self._failure_code, self.result))
        return '<%s state=%s%s>' % (self.__class__.__name__, self.state, extra)

    def _repr_values(self):
        return ''

    def _encode(self):
        raise NotImplementedError()

    def _start(self):
        self._state = ACTION_RUNNING
        self.dispatch_event(EvtActionStarted, action=self)

    def _set_completed(self, msg):
        self._state = ACTION_SUCCEEDED
        self._completed_event_pending = False
        self._dispatch_completed_event(msg)

    def _dispatch_completed_event(self, msg):
        # Override to extra action-specific data from msg and generate
        # an action-specific completion event.  Do not call super if overriden.
        # Must generate a subclass of EvtActionCompleted.
        self._completed_event = EvtActionCompleted(action=self, state=self._state)
        self.dispatch_event(self._completed_event)

    def _set_failed(self, code, reason):
        self._state = ACTION_FAILED
        self._failure_code = code
        self._failure_reason = reason
        self._completed_event_pending = False
        self._completed_event = EvtActionCompleted(action=self, state=self._state,
                                              failure_code=code,
                                              failure_reason=reason)
        self.dispatch_event(self._completed_event)

    def _set_aborting(self, log_abort_messages):
        if not self.is_running:
            raise ValueError("Action isn't currently running")

        if self._enable_abort_logging and log_abort_messages:
            logger.info('Aborting action=%s', self)
        self._state = ACTION_ABORTING


    #### Properties ####

    @property
    def is_running(self):
        '''bool: True if the action is currently in progress.'''
        return self._state == ACTION_RUNNING

    @property
    def is_completed(self):
        '''bool: True if the action has completed (either succeeded or failed).'''
        return self._state in (ACTION_SUCCEEDED, ACTION_FAILED)

    @property
    def is_aborting(self):
        '''bool: True if the action is aborting (will soon be either succeeded or failed).'''
        return self._state == ACTION_ABORTING

    @property
    def has_succeeded(self):
        '''bool: True if the action has succeeded.'''
        return self._state == ACTION_SUCCEEDED

    @property
    def has_failed(self):
        '''bool: True if the action has failed.'''
        return self._state == ACTION_FAILED

    @property
    def failure_reason(self):
        '''tuple of (failure_code, failure_reason): Both values will be None if no failure has occurred.'''
        return (self._failure_code, self._failure_reason)

    @property
    def result(self):
        """An attribute of :class:`ActionResults`: The result of running the action."""
        return self._result

    @property
    def state(self):
        '''string: The current internal state of the action as a string.

        Will match one of the constants:
        :const:`ACTION_IDLE`
        :const:`ACTION_RUNNING`
        :const:`ACTION_SUCCEEDED`
        :const:`ACTION_FAILED`
        :const:`ACTION_ABORTING`
        '''
        return self._state


    #### Private Event Handlers ####

    def _recv_msg_robot_completed_action(self, evt, *, msg):
        result = msg.result
        types = _clad_to_game_cozmo.ActionResult

        self._result = ActionResults.find_by_id(result)
        if self._result is None:
            logger.error("ActionResults has no entry for result id %s", result)

        if result == types.SUCCESS:
            # dispatch to the specific type to extract result info
            self._set_completed(msg)

        elif result == types.RUNNING:
            # XXX what does one do with this? it seems to occur after a cancel request!
            logger.warning('Received "running" action notification for action=%s', self)
            self._set_failed('running', 'Action was still running')

        elif result == types.NOT_STARTED:
            # not sure we'll see this?
            self._set_failed('not_started', 'Action was not started')

        elif result == types.TIMEOUT:
            self._set_failed('timeout', 'Action timed out')

        elif result == types.TRACKS_LOCKED:
            self._set_failed('tracks_locked', 'Action failed due to tracks locked')

        elif result == types.BAD_TAG:
            # guessing this is bad
            self._set_failed('bad_tag', 'Action failed due to bad tag')
            logger.error("Received FAILURE_BAD_TAG for action %s", self)

        elif result == types.CANCELLED_WHILE_RUNNING:
            self._set_failed('cancelled', 'Action was cancelled while running')

        elif result == types.INTERRUPTED:
            self._set_failed('interrupted', 'Action was interrupted')

        else:
            # All other results should fall under either the abort or retry
            # categories, determine the category by shifting the result
            result_category = result >> _clad_to_game_cozmo.ARCBitShift.NUM_BITS
            result_categories = _clad_to_game_cozmo.ActionResultCategory
            
            if result_category == result_categories.ABORT:
                self._set_failed('aborted', 'Action failed')
            elif result_category == result_categories.RETRY:
                self._set_failed('retry', 'Action failed but can be retried')
            else:
                # Shouldn't be able to get here
                self._set_failed('unknown', 'Action failed with unknown reason')
                logger.error('Received unknown action result status %s', msg)


    #### Public Event Handlers ####


    #### Commands ####

    def abort(self, log_abort_messages=False):
        '''Trigger the robot to abort the running action.

        Args:
            log_abort_messages (bool): True to log info on the action that
                is aborted.

        Raises:
            ValueError if the action is not currently being executed.
        '''
        self.robot._action_dispatcher._abort_action(self, log_abort_messages)

    async def wait_for_completed(self, timeout=None):
        '''Waits for the action to complete.

        Args:
            timeout (int or None): Maximum time in seconds to wait for the event.
                Pass None to wait indefinitely.
        Returns:
            The :class:`EvtActionCompleted` event instance
        Raises:
            :class:`asyncio.TimeoutError`
        '''
        if self.is_completed:
            # Already complete
            return self._completed_event
        return await self.wait_for(EvtActionCompleted, timeout=timeout)

    def on_completed(self, handler):
        '''Triggers a handler when the action completes.

        Args:
            handler (callable): An event handler which accepts arguments
                suited to the :class:`EvtActionCompleted` event.
                See :meth:`cozmo.event.add_event_handler` for more information.
        '''
        return self.add_event_handler(EvtActionCompleted, handler)



class _ActionDispatcher(event.Dispatcher):
    _next_action_id = _clad_to_game_cozmo.ActionConstants.FIRST_SDK_TAG

    def __init__(self, robot, **kw):
        super().__init__(**kw)
        self.robot = robot
        self._in_progress = {}
        self._aborting = {}

    def _get_next_action_id(self):
        # Post increment _current_action_id (and loop within the SDK_TAG range)
        next_action_id = self.__class__._next_action_id
        if self.__class__._next_action_id == _clad_to_game_cozmo.ActionConstants.LAST_SDK_TAG:
            self.__class__._next_action_id = _clad_to_game_cozmo.ActionConstants.FIRST_SDK_TAG
        else:
            self.__class__._next_action_id += 1
        return next_action_id

    @property
    def aborting_actions(self):
        '''generator: yields each action that is currently aborting

        Returns:
            A generator yielding :class:`cozmo.action.Action` instances
        '''
        for _, action in self._aborting.items():
            yield action

    @property
    def has_in_progress_actions(self):
        '''bool: True if any SDK-triggered actions are still in progress.'''
        return len(self._in_progress) > 0

    @property
    def in_progress_actions(self):
        '''generator: yields each action that is currently in progress

        Returns:
            A generator yielding :class:`cozmo.action.Action` instances
        '''
        for _, action in self._in_progress.items():
            yield action

    async def wait_for_all_actions_completed(self):
        '''Waits until all actions are complete.

        In this case, all actions include not just in_progress actions but also
        include actions that we're aborting but haven't received a completed message
        for yet.
        '''
        while True:
            action = next(self.in_progress_actions, None)
            if action is None:
                action = next(self.aborting_actions, None)
            if action:
                await action.wait_for_completed()
            else:
                # all actions are now complete
                return

    def _send_single_action(self, action, in_parallel=False, num_retries=0):
        action_id = self._get_next_action_id()
        action.robot = self.robot
        action._action_id = action_id

        if self.has_in_progress_actions and not in_parallel:
            # Note - it doesn't matter if previous action was started as in_parallel,
            # starting any subsequent action with in_parallel==False will cancel
            # any previous actions, so we throw an exception here and require that
            # the client explicitly cancel or wait on earlier actions
            action = list(self._in_progress.values())[0]
            raise exceptions.RobotBusy('Robot is already performing %d action(s) %s' %
                                       (len(self._in_progress), action))

        if action.is_running:
            raise ValueError('Action is already running')

        if action.is_completed:
            raise ValueError('Action already ran')

        if in_parallel:
            position = _clad_to_game_cozmo.QueueActionPosition.IN_PARALLEL
        else:
            position = _clad_to_game_cozmo.QueueActionPosition.NOW

        qmsg = _clad_to_engine_iface.QueueSingleAction(
            idTag=action_id, numRetries=num_retries,
            position=position, action=_clad_to_engine_iface.RobotActionUnion())
        action_msg = action._encode()
        cls_name = action_msg.__class__.__name__
        # For some reason, the RobotActionUnion type uses properties with a lowercase
        # first character, instead of uppercase like all the other unions
        cls_name = cls_name[0].lower() + cls_name[1:]
        setattr(qmsg.action, cls_name, action_msg)
        self.robot.conn.send_msg(qmsg)
        self._in_progress[action_id] = action
        action._start()

    def _is_sdk_action_id(self, action_id):
        return ((action_id >= _clad_to_game_cozmo.ActionConstants.FIRST_SDK_TAG) 
                and (action_id <= _clad_to_game_cozmo.ActionConstants.LAST_SDK_TAG))

    def _is_engine_action_id(self, action_id):
        return ((action_id >= _clad_to_game_cozmo.ActionConstants.FIRST_ENGINE_TAG) 
                and (action_id <= _clad_to_game_cozmo.ActionConstants.LAST_ENGINE_TAG))

    def _is_game_action_id(self, action_id):
        return ((action_id >= _clad_to_game_cozmo.ActionConstants.FIRST_GAME_TAG) 
                and (action_id <= _clad_to_game_cozmo.ActionConstants.LAST_GAME_TAG))

    def _action_id_type(self, action_id):
        if self._is_sdk_action_id(action_id):
            return "sdk"
        elif self._is_engine_action_id(action_id):
            return "engine"
        elif self._is_game_action_id(action_id):
            return "game"
        else:
            return "unknown"

    def _recv_msg_robot_completed_action(self, evt, *, msg):
        action_id = msg.idTag
        is_sdk_action = self._is_sdk_action_id(action_id)
        action = self._in_progress.get(action_id)
        was_aborted = False
        if action is None:
            action = self._aborting.get(action_id)
            was_aborted = action is not None
        if action is None:
            if is_sdk_action:
                logger.error('Received completed action message for unknown SDK action_id=%s', action_id)
            return
        else:
            if not is_sdk_action:
                action_id_type = self._action_id_type(action_id)
                logger.error('Received completed action message for sdk-known %s action_id=%s (was_aborted=%s)',
                             action_id_type, action_id, was_aborted)

        action._completed_event_pending = True

        if was_aborted:
            if action._enable_abort_logging:
                logger.debug('Received completed action message for aborted action=%s', action)
            del self._aborting[action_id]
        else:
            logger.debug('Received completed action message for in-progress action=%s', action)
            del self._in_progress[action_id]
        # XXX This should generate a real event, not a msg
        # Should also dispatch to self so the parent can be notified.
        action.dispatch_event(evt)

    def _abort_action(self, action, log_abort_messages):
        # Mark this in-progress action as aborting - it should get a "Cancelled"
        # message back in the next engine tick, and can basically be considered
        # cancelled from now.
        action._set_aborting(log_abort_messages)

        if action._completed_event_pending:
            # The action was marked as still running but the ActionDispatcher
            # has already received a completion message (and removed it from
            # _in_progress) - the action is just waiting to receive a
            # robot_completed_action message that is still being dispatched
            # via asyncio.ensure_future
            logger.debug('Not sending abort for action=%s to engine as it just completed', action)
        else:
            # move from in-progress to aborting dicts
            self._aborting[action._action_id] = action
            del self._in_progress[action._action_id]

            msg = _clad_to_engine_iface.CancelActionByIdTag(idTag=action._action_id)
            self.robot.conn.send_msg(msg)

    def _abort_all_actions(self, log_abort_messages):
        # Mark any in-progress actions as aborting - they should get a "Cancelled"
        # message back in the next engine tick, and can basically be considered
        # cancelled from now.
        actions_to_abort = self._in_progress
        self._in_progress = {}
        for action_id, action in actions_to_abort.items():
            action._set_aborting(log_abort_messages)
            self._aborting[action_id] = action

        logger.info('Sending abort request for all actions')
        # RobotActionType.UNKNOWN is a wildcard that matches all actions when cancelling.
        msg = _clad_to_engine_iface.CancelAction(actionType=_clad_to_engine_cozmo.RobotActionType.UNKNOWN)
        self.robot.conn.send_msg(msg)

