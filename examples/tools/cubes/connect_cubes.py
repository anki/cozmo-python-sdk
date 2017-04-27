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

'''Connect to Cozmo's cubes.

This script instructs Cozmo to connect to the cubes. This is necessary if you
have previously disconnected from the cubes (to preserve battery life). The
connection process can take up to about 5 seconds.
'''

import cozmo


async def cozmo_program(robot: cozmo.robot.Robot):
    await robot.world.connect_to_cubes()


cozmo.robot.Robot.drive_off_charger_on_connect = False
cozmo.run_program(cozmo_program)
