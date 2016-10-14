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

'''SDK-specific exception classes.'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['CozmoSDKException', 'SDKShutdown', 'StopPropogation',
        'AnimationsNotLoaded', 'ActionError', 'ConnectionError',
        'ConnectionAborted', 'ConnectionCheckFailed', 'NoDevicesFound',
        'SDKVersionMismatch', 'NotPickupable', 'CannotPlaceObjectsOnThis',
        'RobotBusy']


class CozmoSDKException(Exception):
    '''Base class of all Cozmo SDK exceptions.'''

class SDKShutdown(CozmoSDKException):
    '''Raised when the SDK is being shut down'''

class StopPropogation(CozmoSDKException):
    '''Raised by event handlers to prevent further handlers from being triggered.'''

class AnimationsNotLoaded(CozmoSDKException):
    '''Raised if an attempt is made to play a named animation before animations have been received.'''

class ActionError(CozmoSDKException):
    '''Base class for errors that occur with robot actions.'''

class ConnectionError(CozmoSDKException):
    '''Base class for errors regarding connection to the device.'''

class ConnectionAborted(ConnectionError):
    '''Raised if the connection to the device is unexpectedly lost.'''

class ConnectionCheckFailed(ConnectionError):
    '''Raised if the connection check has failed.'''

class NoDevicesFound(ConnectionError):
    '''Raised if no devices connected running Cozmo in SDK mode'''

class SDKVersionMismatch(ConnectionError):
    '''Raised if the Cozmo SDK version is not compatible with the software running on the device.'''

class NotPickupable(ActionError):
    '''Raised if an attempt is made to pick up or place an object that can't be picked up by Cozmo'''

class CannotPlaceObjectsOnThis(ActionError):
    '''Raised if an attempt is made to place an object on top of an invalid object'''

class RobotBusy(ActionError):
    '''Raised if an attempt is made to perform an action while another action is still running.'''
