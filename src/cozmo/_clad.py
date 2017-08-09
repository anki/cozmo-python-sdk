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

__all__ = ['CladEnumWrapper']

import sys

from . import event
from . import logger

from cozmoclad.clad.externalInterface import messageEngineToGame as messageEngineToGame
from cozmoclad.clad.externalInterface import messageGameToEngine as messageGameToEngine

# Shortcut access to CLAD classes
_clad_to_engine_anki = messageGameToEngine.Anki
_clad_to_engine_cozmo = messageGameToEngine.Anki.Cozmo
_clad_to_engine_iface = messageGameToEngine.Anki.Cozmo.ExternalInterface
_clad_to_game_anki = messageEngineToGame.Anki
_clad_to_game_cozmo = messageEngineToGame.Anki.Cozmo
_clad_to_game_iface = messageEngineToGame.Anki.Cozmo.ExternalInterface

# Register event types for engine to game messages
# (e.g. _MsgObjectMoved)
for _name in vars(_clad_to_game_iface.MessageEngineToGame.Tag):
    attrs = {
        '__doc__': 'Internal protocol message',
        'msg': 'Message data'
    }
    _name = '_Msg' + _name
    cls = event._register_dynamic_event_type(_name, attrs)
    globals()[_name] = cls


class CladEnumWrapper:
    """Subclass this for an easy way to wrap a clad-enum in a documentable class.
    
    Call cls._init_class() after declaration of the sub-class to verify the
    type after construction and set up id to type mapping.
    """

    # Override this to the CLAD enum type being wrapped
    _clad_enum = None

    # Override this with the type used for each instance
    # e.g. collections.namedtuple('_ClassName', 'name id')
    _entry_type = None

    _id_to_entry_type = dict()

    @classmethod
    def find_by_id(cls, id):
        return cls._id_to_entry_type.get(id)

    @classmethod
    def _verify(cls, warn_on_missing_definitions=True, add_missing_definitions=True):
        """Verify that definitions are in sync with the underlying CLAD values.

        Optionally also warn about and/or add any missing definitions.

        Args:
            warn_on_missing_definitions (bool): True to warn about any entries
                in the underlying CLAD enum that haven't been explicitly
                declared (includes suggested format for adding, which can then
                be documented with `#:` comments for the generated docs.
            add_missing_definitions (bool): True to automatically add any
                entries in the underlying CLAD enum that haven't been explicitly
                declared. Note that these definitions will work at runtime, but
                won't be present in the auto-generated docs.
        """
        missing_definitions_message = None
        for (_name, _id) in cls._clad_enum.__dict__.items():
            # Ignore any private entries (or internal Python objects) and any
            # "Count" entries in the enum
            if not _name.startswith('_') and (_name != 'Count') and _id >= 0:
                attr = getattr(cls, _name, None)
                if attr is None:
                    # Try the private equivalent with a leading underscore - this
                    # is used when that enum entry is only intended for internal
                    # use and not part of the public API.
                    attr = getattr(cls, "_" + _name, None)
                if attr is not None:
                    if attr.id != _id:
                        sys.exit(
                            'Incorrect definition in %s for id %s=%s, (should =%s) - line should read:\n'
                            '%s = _entry_type("%s", _clad_enum.%s)'
                            % (str(cls), _name, attr.id, _id, _name, _name, _name))
                else:
                    if warn_on_missing_definitions:
                        if missing_definitions_message is None:
                            missing_definitions_message = ('\nMissing definition(s) in %s - to document them add:\n' % str(cls))
                        missing_definitions_message += ('    %s = _entry_type("%s", _clad_enum.%s)\n' % (_name, _name, _name))
                    if add_missing_definitions:
                        setattr(cls, _name, cls._entry_type(_name, _id))

        if missing_definitions_message is not None:
            logger.warning(missing_definitions_message)

    @classmethod
    def _build_id_to_entry_type(cls):
        # populate _id_to_entry_type mapping
        for (_name, _entry) in cls.__dict__.items():
            if isinstance(_entry, cls._entry_type):
                cls._id_to_entry_type[_entry.id] = _entry

    @classmethod
    def _init_class(cls, warn_on_missing_definitions=True, add_missing_definitions=True):
        cls._verify(warn_on_missing_definitions, add_missing_definitions)
        cls._build_id_to_entry_type()
