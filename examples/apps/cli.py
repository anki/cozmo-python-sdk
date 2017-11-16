#!/usr/bin/env python3

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

'''Command Line Interface for Cozmo

This is an example of integrating Cozmo with an ipython-based command line interface.
'''

import sys

try:
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.terminal.prompts import Prompts, Token
except ImportError:
    sys.exit('Cannot import from ipython: Do `pip3 install ipython` to install')

import cozmo

usage = ('This is an IPython interactive shell for Cozmo.\n'
         'All commands are executed within cozmo\'s running program loop.\n'
         'Use the [tab] key to auto-complete commands, and see all available methods.\n'
         'All IPython commands work as usual. See below for some useful syntax:\n'
         '  ?         -> Introduction and overview of IPython\'s features.\n'
         '  object?   -> Details about \'object\'.\n'
         '  object??  -> More detailed, verbose information about \'object\'.')

# Creating IPython's history database on the main thread
ipyshell = InteractiveShellEmbed(banner1='\nWelcome to the Cozmo Shell',
                                 exit_msg='Goodbye\n')

def cozmo_program(robot: cozmo.robot.Robot):
    '''Invoke the ipython shell while connected to cozmo'''
    default_log_level = cozmo.logger.level
    cozmo.logger.setLevel('WARN')
    ipyshell(usage)
    cozmo.logger.setLevel(default_log_level)

cozmo.run_program(cozmo_program, use_3d_viewer=True, use_viewer=True)
