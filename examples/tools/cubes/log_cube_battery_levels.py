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

'''Log the battery level of all connected cubes.

This script can be used to verify which cubes are connected, and the current
battery levels of each cube. This script can take several seconds to get the
battery levels as they're only sent intermittently.
'''

import asyncio

import cozmo
from cozmo.objects import LightCube1Id, LightCube2Id, LightCube3Id


async def log_cube_info(robot: cozmo.robot.Robot, cube_id):
    cube = robot.world.get_light_cube(cube_id)
    if cube is not None:
        # Wait for up to few seconds for the cube to have received battery level info
        for i in range(30):
            if cube.battery_voltage is None:
                if i == 0:
                    cozmo.logger.info("Cube %s waiting for battery info...", cube_id)
                await asyncio.sleep(0.5)
            else:
                break
        cozmo.logger.info("Cube %s battery = %s", cube_id, cube.battery_str)
    else:
        cozmo.logger.warning("Cube %s is not connected - check the battery.", cube_id)


async def cozmo_program(robot: cozmo.robot.Robot):
    await log_cube_info(robot, LightCube1Id)  # looks like a paperclip
    await log_cube_info(robot, LightCube2Id)  # looks like a lamp / heart
    await log_cube_info(robot, LightCube3Id)  # looks like the letters 'ab' over 'T'


cozmo.robot.Robot.drive_off_charger_on_connect = False
cozmo.run_program(cozmo_program)
