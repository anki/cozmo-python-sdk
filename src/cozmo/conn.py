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

'''Engine connection.

The SDK operates by connecting to the Cozmo "engine" - typically the Cozmo
app that runs on an iOS or Android device.

The engine is responsible for much of the work that Cozmo does, including
image recognition, path planning, behaviors and animation handling, etc.

The :mod:`cozmo.run` module takes care of opening a connection over a USB
connection to a device, but the :class:`CozmoConnection` class defined in
this module does the work of relaying messages to and from the engine and
dispatching them to the :class:`cozmo.robot.Robot` instance.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['EvtRobotFound', 'CozmoConnection']


import asyncio
import platform

import cozmoclad

from . import logger
from . import anim
from . import clad_protocol
from . import event
from . import exceptions
from . import robot
from . import version

from . import _clad
from ._clad import _clad_to_engine_cozmo, _clad_to_engine_iface, _clad_to_game_cozmo, _clad_to_game_iface


class EvtConnected(event.Event):
    '''Triggered when the initial connection to the device has been established.

    This connection is setup before contacting the robot - Wait for EvtRobotFound
    or EvtRobotReady for a usefully configured Cozmo instance.
    '''
    conn = 'The connected CozmoConnection object'


class EvtRobotFound(event.Event):
    '''Triggered when a Cozmo robot is detected, but before he's initialized.

    :class:`cozmo.robot.EvtRobotReady` is dispatched when the robot is fully initialized.
    '''
    robot = 'The Cozmo object for the robot'


class EvtConnectionClosed(event.Event):
    '''Triggered when the connection to the controlling device is closed.
    '''
    exc = 'The exception that triggered the closure, or None'


# Some messages have no robotID but should still be forwarded to the primary robot
FORCED_ROBOT_MESSAGES = {"AnimationAborted",
                         "AnimationEvent",
                         "BehaviorObjectiveAchieved",
                         "BehaviorTransition",
                         "BlockPickedUp",
                         "BlockPlaced",
                         "BlockPoolDataMessage",
                         "CarryStateUpdate",
                         "ChargerEvent",
                         "ConnectedObjectStates",
                         "CreatedFixedCustomObject",
                         "CubeLightsStateTransition",
                         "CurrentCameraParams",
                         "DefinedCustomObject",
                         "DeviceAccelerometerValuesRaw",
                         "DeviceAccelerometerValuesUser",
                         "DeviceGyroValues",
                         "IsDeviceIMUSupported",
                         "LoadedKnownFace",
                         "LocatedObjectStates",
                         "MemoryMapMessage",
                         "MemoryMapMessageBegin",
                         "MemoryMapMessageEnd",
                         "ObjectAccel",
                         "ObjectAvailable",
                         "ObjectConnectionState",
                         "ObjectMoved",
                         "ObjectPowerLevel",
                         "ObjectProjectsIntoFOV",
                         "ObjectStoppedMoving",
                         "ObjectTapped",
                         "ObjectTappedFiltered",
                         "ObjectUpAxisChanged",
                         "PerRobotSettings",
                         "ReactionaryBehaviorTransition",
                         "RobotChangedObservedFaceID",
                         "RobotCliffEventFinished",
                         "RobotCompletedAction",
                         "RobotDeletedAllCustomObjects",
                         "RobotDeletedCustomMarkerObjects",
                         "RobotDeletedFixedCustomObjects",
                         "RobotDelocalized",
                         "RobotErasedAllEnrolledFaces",
                         "RobotErasedEnrolledFace",
                         "RobotObservedFace",
                         "RobotObservedMotion",
                         "RobotObservedObject",
                         "RobotObservedPet",
                         "RobotObservedPossibleObject",
                         "RobotOnChargerPlatformEvent",
                         "RobotPoked",
                         "RobotReachedEnrollmentCount",
                         "RobotRenamedEnrolledFace",
                         "RobotState",
                         "UnexpectedMovement"}


class CozmoConnection(event.Dispatcher, clad_protocol.CLADProtocol):
    '''Manages the connection to the Cozmo app to communicate with the core engine.

    An instance of this class is passed to functions used with
    :func:`cozmo.run.connect`.  At the point the function is executed,
    the connection is already established and verified, and the
    :class:`EvtConnected` has already been sent.

    However, after the initial connection is established, programs will usually
    want to call :meth:`wait_for_robot` to wait for an actual Cozmo robot to
    be detected and initialized before doing useful work.
    '''

    #: callable: The factory function that returns a
    #: :class:`cozmo.robot.Robot` class or subclass instance.
    robot_factory = robot.Robot

    #: callable: The factory function that returns an
    #: :class:`cozmo.anim.AnimationNames` class or subclass instance.
    anim_names_factory = anim.AnimationNames

    # overrides for CLADProtocol
    clad_decode_union = _clad_to_game_iface.MessageEngineToGame
    clad_encode_union = _clad_to_engine_iface.MessageGameToEngine

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._is_connected = False
        self._is_ui_connected = False
        self._running = True
        self._robots = {}
        self._primary_robot = None

        #: A dict containing information about the device the connection is using.
        self.device_info = {}

        #: An :class:`cozmo.anim.AnimationNames` object that references all
        #: available animation names
        self.anim_names = self.anim_names_factory(self)


    #### Private Methods ####

    def __repr__(self):
        info = ' '.join(['%s="%s"' % (k, self.device_info[k])
            for k in sorted(self.device_info.keys())])
        return '<%s %s>' % (self.__class__.__name__, info)

    def connection_made(self, transport):
        super().connection_made(transport)
        self._is_connected = True

    def connection_lost(self, exc):
        super().connection_lost(exc)
        self._is_connected = False
        if self._running:
            self.abort(exceptions.ConnectionAborted("Lost connection to the device"))
            logger.error("Lost connection to the device: %s", exc)

    async def shutdown(self):
        '''Close the connection to the device.'''
        if self._running and self._is_connected:
            logger.info("Shutting down connection")
            self._running = False
            event._abort_futures(exceptions.SDKShutdown())
            self._stop_dispatcher()
            self.transport.close()

    def abort(self, exc):
        '''Abort the connection to the device.'''
        if self._running:
            logger.info('Aborting connection: %s', exc)
            self._running = False
            # Allow any currently pending futures to complete before the
            # remainder are aborted.
            self._loop.call_soon(lambda: event._abort_futures(exc))
            self._stop_dispatcher()
            self.transport.close()


    def msg_received(self, msg):
        '''Receives low level communication messages from the engine.'''
        if not self._running:
            return

        try:
            tag_name = msg.tag_name

            if tag_name == 'Ping':
                # short circuit to avoid unnecessary event overhead
                return self._handle_ping(msg._data)

            elif tag_name == 'UiDeviceConnected':
                # handle outside of event dispatch for quick abort in case
                # of a version mismatch problem.
                return self._handle_ui_device_connected(msg._data)

            msg = msg._data
            robot_id = getattr(msg, 'robotID', None)

            event_name = '_Msg' +  tag_name

            evttype = getattr(_clad, event_name, None)
            if evttype is None:
                logger.error('Received unknown CLAD message %s', event_name)
                return

            # Dispatch messages to the robot if they either:
            # a) are explicitly white listed in FORCED_ROBOT_MESSAGES
            # b) have a robotID specified in the message
            # Otherwise dispatch the message through this connection.
            if (robot_id is not None) or (tag_name in FORCED_ROBOT_MESSAGES):
                if robot_id is None:
                    # The only robot ID ever used is 1, so it is safe to assume that here as a default.
                    robot_id = 1
                self._process_robot_msg(robot_id, evttype, msg)
            else:
                self.dispatch_event(evttype, msg=msg)

        except Exception as exc:
            # No exceptions should reach this point; it's a bug if they do.
            self.abort(exc)

    def _process_robot_msg(self, robot_id, evttype, msg):
        if robot_id != 1:
            # Note: some messages replace robotID with value!=1 (like mfgID for example)
            #       as a result, this log may fire quite often. Log Level is set to debug
            #       since it suppressed by default (prevents spamming).
            logger.debug('INVALID ROBOT_ID SEEN robot_id=%s event=%s msg=%s', robot_id, evttype, msg.__str__())
            robot_id = 1 # XXX remove when errant messages have been fixed

        # Note: this code constructs the robot if it doesn't exist at this time
        robot = self._robots.get(robot_id)
        if not robot:
            logger.info('Found robot id=%s', robot_id)
            robot = self.robot_factory(self, robot_id, is_primary=self._primary_robot is None)
            self._robots[robot_id] = robot
            if not self._primary_robot:
                self._primary_robot = robot
            # Dispatch an event notifying that a new robot has been found
            # the robot itself will send EvtRobotReady after initialization
            self.dispatch_event(EvtRobotFound, robot=robot)

            # _initialize will set the robot to a known good state in the
            # background and dispatch a EvtRobotReady event when completed.
            robot._initialize()

        robot.dispatch_event(evttype, msg=msg)


    #### Properties ####

    @property
    def is_connected(self):
        '''bool: True if currently connected to the remote engine.'''
        return self._is_connected


    #### Private Event handlers ####

    def _handle_ping(self, msg):
        '''Respond to a ping event.'''
        if msg.isResponse:
            # To avoid duplication, pings originate from engine, and engine
            # accumulates the latency info from the responses
            logger.error("Only engine should receive responses")
        else:
            resp = _clad_to_engine_iface.Ping(
                counter=msg.counter,
                timeSent_ms=msg.timeSent_ms,
                isResponse=True)
            self.send_msg(resp)

    def _recv_default_handler(self, event, **kw):
        '''Default event handler.'''
        if event.event_name.startswith('msg_animation'):
            return self.anim.dispatch_event(event)

        logger.debug('Engine received unhandled event_name=%s  kw=%s', event, kw)

    def _recv_msg_animation_available(self, evt, msg):
        self.anim_names.dispatch_event(evt)

    def _recv_msg_end_of_message(self, evt, *a, **kw):
        self.anim_names.dispatch_event(evt)

    def _handle_ui_device_connected(self, msg):
        if msg.connectionType != _clad_to_engine_cozmo.UiConnectionType.SdkOverTcp:
            # This isn't for us
            return

        if msg.deviceID != 1:
            logger.error('Unexpected Device Id %s', msg.deviceID)
            return

        # Verify that engine and SDK are compatible
        clad_hashes_match = False
        try:
            cozmoclad.assert_clad_match(msg.toGameCLADHash, msg.toEngineCLADHash)
            clad_hashes_match = True
        except cozmoclad.CLADHashMismatch as exc:
            logger.error(exc)

        build_versions_match = (cozmoclad.__build_version__ == '00000.00000.00000'
            or cozmoclad.__build_version__ == msg.buildVersion)

        if clad_hashes_match and not build_versions_match:
            # If CLAD hashes match, and this is only a minor version change,
            # then still allow connection (it's just an app hotfix
            # that didn't require CLAD or SDK changes)
            sdk_major_version = cozmoclad.__build_version__.split(".")[0:2]
            build_major_version = msg.buildVersion.split(".")[0:2]
            build_versions_match = (sdk_major_version == build_major_version)

        if clad_hashes_match and build_versions_match:
            connection_success_msg = _clad_to_engine_iface.UiDeviceConnectionSuccess(
                connectionType=msg.connectionType,
                deviceID=msg.deviceID,
                buildVersion = cozmoclad.__version__,
                sdkModuleVersion = version.__version__,
                pythonVersion = platform.python_version(),
                pythonImplementation = platform.python_implementation(),
                osVersion = platform.platform(),
                cpuVersion = platform.machine())

            self.send_msg(connection_success_msg)

        else:
            try:
                wrong_version_msg = _clad_to_engine_iface.UiDeviceConnectionWrongVersion(
                    reserved=0,
                    connectionType=msg.connectionType,
                    deviceID = msg.deviceID,
                    buildVersion = cozmoclad.__version__)

                self.send_msg(wrong_version_msg)
            except AttributeError:
                pass

            line_separator = "=" * 80
            error_message = "\n" + line_separator + "\n"

            def _trimmed_version(ver_string):
                # Trim leading zeros from the version string.
                trimmed_string = ""
                for i in ver_string.split("."):
                    trimmed_string += str(int(i)) + "."
                return trimmed_string[:-1]  # remove trailing "."

            if not build_versions_match:
                error_message += ("App and SDK versions do not match!\n"
                                  "----------------------------------\n"
                                  "SDK's cozmoclad version: %s\n"
                                  "         != app version: %s\n\n"
                                  % (cozmoclad.__version__, _trimmed_version(msg.buildVersion)))

                if cozmoclad.__build_version__ < msg.buildVersion:
                    # App is newer
                    error_message += ('Please update your SDK to the newest version by calling command:\n'
                                      '"pip3 install --user --upgrade cozmo"\n'
                                      'and downloading the latest examples from:\n'
                                      'http://cozmosdk.anki.com/docs/downloads.html\n')
                else:
                    # SDK is newer
                    error_message += ('Please either:\n\n'
                                      '1) Update your app to the most recent version on the app store.\n'
                                      '2) Or, if you prefer, please determine which SDK version matches\n'
                                      '   your app version at: http://go.anki.com/cozmo-sdk-version\n'
                                      '   Then downgrade your SDK by calling the following command,\n'
                                      '   replacing SDK_VERSION with the version listed at that page:\n'
                                      '   "pip3 install --ignore-installed cozmo==SDK_VERSION"\n')

            else:
                # CLAD version mismatch
                error_message += ('CLAD Hashes do not match!\n'
                                  '-------------------------\n'
                                  'Your Python and C++ CLAD versions do not match - connection refused.\n'
                                  'Please check that you have the most recent versions of both the SDK and the\n'
                                  'Cozmo app. You may update your SDK by calling:\n'
                                  '"pip3 install --user --upgrade cozmo".\n'
                                  'Please also check the app store for a Cozmo app update.\n')

            error_message += line_separator
            logger.error(error_message)

            exc = exceptions.SDKVersionMismatch("SDK library does not match software running on device",
                                                sdk_version=version.__version__,
                                                sdk_app_version=cozmoclad.__version__,
                                                app_version=_trimmed_version(msg.buildVersion))

            self._abort_connection = True  # Ignore remaining messages - they're not safe to unpack

            self.abort(exc)
            return

        self._is_ui_connected = True
        self.dispatch_event(EvtConnected, conn=self)

        logger.info('App connection established. sdk_version=%s '
                'cozmoclad_version=%s app_build_version=%s',
                version.__version__, cozmoclad.__version__, msg.buildVersion)

        # We send RequestConnectedObjects and RequestLocatedObjectStates before
        # refreshing the animation names as this ensures that we will receive
        # the responses before we mark the robot as ready.
        self._request_connected_objects()
        self._request_located_objects()

        self.anim_names.refresh()

    def _request_connected_objects(self):
        # Request information on connected objects (e.g. the object ID of each cube)
        # (this won't provide location/pose info)
        msg = _clad_to_engine_iface.RequestConnectedObjects()
        self.send_msg(msg)

    def _request_located_objects(self):
        # Request the pose information for all objects whose location we know
        # (this won't include any objects where the location is currently not known)
        msg = _clad_to_engine_iface.RequestLocatedObjectStates()
        self.send_msg(msg)

    def _recv_msg_image_chunk(self, evt, *, msg):
        if self._primary_robot:
            self._primary_robot.dispatch_event(evt)

    #### Public Event Handlers ####

    #### Commands ####

    async def _wait_for_robot(self, timeout=5):
        if not self._primary_robot:
            await self.wait_for(EvtRobotFound, timeout=timeout)
        if self._primary_robot.is_ready:
            return self._primary_robot
        await self._primary_robot.wait_for(robot.EvtRobotReady, timeout=timeout)
        return self._primary_robot

    async def wait_for_robot(self, timeout=5):
        '''Wait for a Cozmo robot to connect and complete initialization.

        Args:
            timeout (float): Maximum length of time to wait for a robot to be ready in seconds.
        Returns:
            A :class:`cozmo.robot.Robot` instance that's ready to use.
        Raises:
            :class:`asyncio.TimeoutError` if there's no response from the robot.
        '''
        try:
            robot = await self._wait_for_robot(timeout)
            if robot and robot.drive_off_charger_on_connect:
                await robot.drive_off_charger_contacts().wait_for_completed()
        except asyncio.TimeoutError:
            logger.error('Timed out waiting for robot to initialize')
            raise
        return robot
