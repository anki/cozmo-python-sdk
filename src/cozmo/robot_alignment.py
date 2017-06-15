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
from ._clad import _clad_to_engine_cozmo

_RobotAlignmentType = collections.namedtuple('_RobotAlignmentType', ['name', 'id'])

try:
    class RobotAlignmentTypes:
        '''Defines all robot alignment types.
        '''
        #: Align the tips of the lift fingers with the target object
        LiftFinger = _RobotAlignmentType("LiftFinger", _clad_to_engine_cozmo.AlignmentType.LIFT_FINGER)

        #: Align the flat part of the life with the object
        #: (Useful for getting the fingers in the cube's grooves)
        LiftPlate = _RobotAlignmentType("LiftPlate", _clad_to_engine_cozmo.AlignmentType.LIFT_PLATE)

        #: Align the front of cozmo's body
        #: (Useful for when the lift is up)
        Body = _RobotAlignmentType("Body", _clad_to_engine_cozmo.AlignmentType.BODY)

        #: For use with distanceFromMarker parameter
        Custom = _RobotAlignmentType("Custom", _clad_to_engine_cozmo.AlignmentType.CUSTOM)

        _id_to_robot_alignment_type = dict()

        @classmethod
        def find_by_id(cls, id):
            return cls._id_to_robot_alignment_type.get(id)

    # populate RobotAlignmentTypes _id_to_alignment_type mapping
    for (_name, _rat) in RobotAlignmentTypes.__dict__.items():
        if isinstance(_rat, _RobotAlignmentType):
            RobotAlignmentTypes._id_to_robot_alignment_type[_rat.id] = _rat

except AttributeError as exc:
    err = ('Incorrect version of cozmoclad package installed.  '
            'run "pip3 install --user --ignore-installed cozmoclad==%s" '
            '(error: %s in robot_alignment.py)' % (__cozmoclad_version__, exc))
    raise ImportError(err) from exc
