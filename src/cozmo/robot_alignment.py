# Copyright (c) 2017 Anki, Inc.
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
RobotAlignment related classes, functions, events and values.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['RobotAlignmentTypes']

import collections

from ._clad import _clad_to_engine_cozmo, CladEnumWrapper

_RobotAlignmentType = collections.namedtuple('_RobotAlignmentType', ['name', 'id'])


class RobotAlignmentTypes(CladEnumWrapper):
    '''Defines all robot alignment types.
    '''
    _clad_enum = _clad_to_engine_cozmo.AlignmentType
    _entry_type = _RobotAlignmentType

    #: Align the tips of the lift fingers with the target object
    LiftFinger = _entry_type("LiftFinger", _clad_enum.LIFT_FINGER)

    #: Align the flat part of the lift with the object
    #: (Useful for getting the fingers in the cube's grooves)
    LiftPlate = _entry_type("LiftPlate", _clad_enum.LIFT_PLATE)

    #: Align the front of cozmo's body
    #: (Useful for when the lift is up)
    Body = _entry_type("Body", _clad_enum.BODY)

    #: For use with distanceFromMarker parameter
    Custom = _entry_type("Custom", _clad_enum.CUSTOM)

RobotAlignmentTypes._init_class()
