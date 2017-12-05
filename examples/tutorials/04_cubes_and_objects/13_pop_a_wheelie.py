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

'''Tell Cozmo to pop a wheelie on a cube that is placed in front of him.

This example demonstrates Cozmo driving to a cube and pushing himself onto
his back by pushing his lift against that cube.
'''

import cozmo

async def pop_a_wheelie(robot: cozmo.robot.Robot):
    print("Cozmo is waiting until he sees a cube")
    cube = await robot.world.wait_for_observed_light_cube()

    print("Cozmo found a cube, and will now attempt to pop a wheelie on it")

    action = robot.pop_a_wheelie(cube, num_retries=2)
    await action.wait_for_completed()


cozmo.run_program(pop_a_wheelie)
