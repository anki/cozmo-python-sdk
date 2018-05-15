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

'''Tell Cozmo to roll a cube that is placed in front of him.

This example demonstrates Cozmo driving to and rolling a cube.
You must place a cube in front of Cozmo so that he can see it.
The cube should be centered in front of him.
'''

import cozmo
from cozmo.util import degrees

async def roll_a_cube(robot: cozmo.robot.Robot):
    await robot.set_head_angle(degrees(-5.0)).wait_for_completed()

    print("Cozmo is waiting until he sees a cube")
    cube = await robot.world.wait_for_observed_light_cube()

    print("Cozmo found a cube, and will now attempt to roll with it:")
    # Cozmo will approach the cube he has seen and roll it
    # check_for_object_on_top=True enforces that Cozmo will not roll cubes with anything on top
    action = robot.roll_cube(cube, check_for_object_on_top=True, num_retries=2)
    await action.wait_for_completed()
    print("result:", action.result)

cozmo.run_program(roll_a_cube)
