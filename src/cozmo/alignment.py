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
Alignment related classes, functions, events and values.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['AlignmentTypes']

import collections
from ._clad import _clad_to_engine_cozmo

_AlignmentType = collections.namedtuple('_AlignmentType', ['name', 'id'])

try:
    class AlignmentTypes:
        '''Defines all robot alignment types.
        '''

        LiftFinger = _AlignmentType("LiftFinger", _clad_to_engine_cozmo.AlignmentType.LIFT_FINGER)

        LiftPlate = _AlignmentType("LiftPlate", _clad_to_engine_cozmo.AlignmentType.LIFT_PLATE)

        Body = _AlignmentType("Body", _clad_to_engine_cozmo.AlignmentType.BODY)

        Custom = _AlignmentType("Custom", _clad_to_engine_cozmo.AlignmentType.CUSTOM)

        _id_to_behavior_type = dict()

        @classmethod
        def find_by_id(cls, id):
            return cls._id_to_behavior_type.get(id)

    # populate AlignmentTypes _id_to_alignment_type mapping
    for (_name, _bt) in AlignmentTypes.__dict__.items():
        if isinstance(_bt, _AlignmentType):
            AlignmentTypes._id_to_behavior_type[_bt.id] = _bt

except AttributeError as exc:
    err = ('Incorrect version of cozmoclad package installed.  '
            'run "pip3 install --user --ignore-installed cozmoclad==%s" '
            '(error: %s in behavior.py)' % (__cozmoclad_version__, exc))
    raise ImportError(err) from exc
