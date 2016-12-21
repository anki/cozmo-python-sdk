#!/usr/bin/env python3

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

'''Control Cozmo's Backpack lights

This script shows how you can control Cozmo's backpack lights and set
them to different colors.
'''

import time

import cozmo


def cozmo_program(robot: cozmo.robot.Robot):
    # set all of Cozmo's backpack lights to red, and wait for 2 seconds
    robot.set_all_backpack_lights(cozmo.lights.red_light)
    time.sleep(2)
    # set all of Cozmo's backpack lights to green, and wait for 2 seconds
    robot.set_all_backpack_lights(cozmo.lights.green_light)
    time.sleep(2)
    # set all of Cozmo's backpack lights to blue, and wait for 2 seconds
    robot.set_all_backpack_lights(cozmo.lights.blue_light)
    time.sleep(2)
    # set just Cozmo's center backpack lights to white, and wait for 2 seconds
    robot.set_center_backpack_lights(cozmo.lights.white_light)
    time.sleep(2)
    # turn off Cozmo's backpack lights and wait for 2 seconds
    robot.set_all_backpack_lights(cozmo.lights.off_light)
    time.sleep(2)


cozmo.run_program(cozmo_program)
