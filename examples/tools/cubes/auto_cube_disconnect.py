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

'''Set whether Cozmo should automatically disconnect from cubes after each SDK program.

This script can be used to turn auto cube disconnection on or off (using command
line arguments -e or -d). Automatic disconnection can be used to help conserve
cube battery life between SDK program runs. You can use `connect_cubes.py` later
to re-connect to the cubes.
'''

import argparse

import cozmo


async def cozmo_program(robot: cozmo.robot.Robot):
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--enable',
                        dest='enable_auto_disconnect',
                        default=False,
                        action='store_const',
                        const=True,
                        help='Enable auto cube disconnection')
    parser.add_argument('-d', '--disable',
                        dest='disable_auto_disconnect',
                        default=False,
                        action='store_const',
                        const=True,
                        help='Disable auto cube disconnection')
    options = parser.parse_args()

    if options.enable_auto_disconnect:
        robot.world.auto_disconnect_from_cubes_at_end(True)
    elif options.disable_auto_disconnect:
        robot.world.auto_disconnect_from_cubes_at_end(False)
    else:
        cozmo.logger.error("Incorrect options provided, see:")
        parser.print_help()


cozmo.robot.Robot.drive_off_charger_on_connect = False
cozmo.run_program(cozmo_program)
