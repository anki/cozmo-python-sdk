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

'''Tell Cozmo to drive up to a cube that he sees placed in front of him

This is a test / example usage of the robot.roll_cube call which creates a
RollCube action, that can be used to drive and roll a LightCube
'''

import asyncio
import cozmo

async def roll_cube_test(robot: cozmo.robot.Robot):
    '''The core of the dock with cube test program'''

    # Wait for a cube to appear in front of cosmo's space
    cube = await robot.world.wait_for_observed_light_cube()
    
    ''' Tell cozmo to approach the cube and roll it.
    we are including the optional check_for_object_on_top parameter
    which will cause cozmo to ignore this cube if it is in a stack.

    The roll behavior can be perfomed on a stack, but may have less
    reliable results.
    '''
    await robot.roll_cube( cube, check_for_object_on_top=True ).wait_for_completed()

cozmo.run_program(roll_cube_test)
