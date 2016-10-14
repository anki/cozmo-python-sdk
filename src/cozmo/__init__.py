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
from . import lcd_face
from . import lights
from . import objects
from . import robot
from . import run
from . import util
from . import world

from .exceptions import *
from .run import *

from .version import __version__, __cozmoclad_version__


__all__ = ['logger', 'logger_protocol'] + \
    ['action', 'anim', 'annotate', 'behavior', 'conn', 'event', 'exceptions'] + \
    ['lcd_face', 'lights', 'objects', 'robot', 'run', 'util', 'world'] + \
        (run.__all__ + exceptions.__all__)
