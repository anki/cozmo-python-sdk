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

import sys
if sys.version_info < (3,5,1):
    sys.exit('cozmo requires Python 3.5.1 or later')

# Verify cozmoclad version before any other imports, so we can catch a mismatch
# before triggering any exceptions from missing clad definitions
try:
    from cozmoclad import __build_version__ as __installed_cozmoclad_build_version__
except ImportError as e:
    sys.exit("%s\nCannot import from cozmoclad: Do `pip3 install --user cozmoclad` to install" % e)

from .version import __version__, __cozmoclad_version__, __min_cozmoclad_version__

def verify_min_clad_version():
    def _make_sortable_version_string(ver_string):
        # pad out an x.y.z version to a 5.5.5 string with leading zeroes
        ver_elements = [str(int(x)).zfill(5) for x in ver_string.split(".")]
        return '.'.join(ver_elements)

    def _trimmed_version(ver_string):
        # Trim leading zeros from the version string
        trimmed_parts = [str(int(x)) for x in ver_string.split(".")]
        return '.'.join(trimmed_parts)

    min_cozmoclad_version_str = _make_sortable_version_string(__min_cozmoclad_version__)
    if __installed_cozmoclad_build_version__ < min_cozmoclad_version_str:
        sys.exit("Incompatible cozmoclad version %s for SDK %s - needs at least %s\n"
                 "Do `pip3 install --user --upgrade cozmoclad` to upgrade" % (
            _trimmed_version(__installed_cozmoclad_build_version__),
            __version__,
            __min_cozmoclad_version__))


verify_min_clad_version()


import logging as _logging

#: The general purpose logger logs high level information about Cozmo events.
logger = _logging.getLogger('cozmo.general')

#: The protocol logger logs low level messages that are sent back and forth to Cozmo.
logger_protocol = _logging.getLogger('cozmo.protocol')

del _logging

from . import action
from . import anim
from . import annotate
from . import behavior
from . import conn
from . import event
from . import exceptions
from . import lights
from . import nav_memory_map
from . import objects
from . import oled_face
from . import robot
from . import robot_alignment
from . import run
from . import util
from . import world

from .exceptions import *
from .run import *


__all__ = ['logger', 'logger_protocol',
           'action', 'anim', 'annotate', 'behavior', 'conn', 'event',
           'exceptions', 'lights', 'objects', 'oled_face', 'nav_memory_map',
           'robot', 'robot_alignment', 'run', 'util', 'world'] + \
          (run.__all__ + exceptions.__all__)
