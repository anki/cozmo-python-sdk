# Copyright (c) 2018 Anki, Inc.
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
Song related classes, functions, events and values.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['NoteTypes', 'NoteDurations', 'SongNote']

import collections

from . import logger

from . import action
from . import exceptions
from . import event

from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo, _clad_to_engine_anki, CladEnumWrapper

# generate names for each CLAD defined Note Type
class _NoteType(collections.namedtuple('_NoteType', 'name id')):
    # Tuple mapping between CLAD SongNoteType. name and ID
    # All instances will be members of NoteTypes

    # Keep _NoteType as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'NoteTypes.%s' % self.name


class NoteTypes(CladEnumWrapper):
    """The possible values for an NoteType.

    A pitch between C2 and C3_Sharp can be specified,
    as well as a rest (for timed silence), giving
    cozmo a vocal range of slightly more than one
    octave.

    B_Flat and E_Flat are represented as their corresponding
    sharps.
    """
    _clad_enum = _clad_to_engine_iface.SongNoteType
    _entry_type = _NoteType

    #: 
    C2       = _entry_type("C2", _clad_enum.C2)
    #: 
    C2_Sharp = _entry_type("C2_Sharp", _clad_enum.C2_Sharp)
    #: 
    D2       = _entry_type("D2", _clad_enum.D2)
    #: 
    D2_Sharp = _entry_type("D2_Sharp", _clad_enum.D2_Sharp)
    #: 
    E2       = _entry_type("E2", _clad_enum.E2)
    #: 
    F2       = _entry_type("F2", _clad_enum.F2)
    #: 
    F2_Sharp = _entry_type("F2_Sharp", _clad_enum.F2_Sharp)
    #: 
    G2       = _entry_type("G2", _clad_enum.G2)
    #: 
    G2_Sharp = _entry_type("G2_Sharp", _clad_enum.G2_Sharp)
    #: 
    A2       = _entry_type("A2", _clad_enum.A2)
    #: 
    A2_Sharp = _entry_type("A2_Sharp", _clad_enum.A2_Sharp)
    #: 
    B2       = _entry_type("B2", _clad_enum.B2)
    #: 
    C3       = _entry_type("C3", _clad_enum.C3)
    #: 
    C3_Sharp = _entry_type("C3_Sharp", _clad_enum.C3_Sharp)
    #: 
    Rest     = _entry_type("Rest", _clad_enum.Rest)

NoteTypes._init_class(warn_on_missing_definitions=True)


# generate names for each CLAD defined Note Duration
class _NoteDuration(collections.namedtuple('_NoteDuration', 'name id')):
    # Tuple mapping between CLAD SongNoteDuration. name and ID
    # All instances will be members of NoteTypes

    # Keep _NoteDuration as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'NoteDurations.%s' % self.name


class NoteDurations(CladEnumWrapper):
    """The possible values for a NoteDuration.
    """
    _clad_enum = _clad_to_engine_iface.SongNoteDuration
    _entry_type = _NoteDuration

    #: 
    Whole        = _entry_type("Whole", _clad_enum.Whole)
    #: 
    ThreeQuarter = _entry_type("ThreeQuarter", _clad_enum.ThreeQuarter)
    #: 
    Half         = _entry_type("Half", _clad_enum.Half)
    #: 
    Quarter      = _entry_type("Quarter", _clad_enum.Quarter)

NoteDurations._init_class(warn_on_missing_definitions=True)


class SongNote(_clad_to_engine_iface.SongNote):
    """Represents on element in a song.  Consists of a :class:`cozmo.song.NoteTypes` which specifies
    either a pitch or rest, and a :class:`cozmo.song.NoteDurations` specifying the length of the
    note.
    """
    def __init__(self, noteType=NoteTypes.C2, noteDuration=NoteDurations.Whole):
        super(SongNote, self).__init__(noteType.id, noteDuration.id)
