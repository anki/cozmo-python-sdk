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

'''Control Cozmo with simple scripts.


This script is made to show a bunch of interesting one liners you can do with Cozmo.
He will set his backpack lights to red
Play an angry animation
Drive 100mm backwards (at 50mm per second)
Play a react to cliff animation
Then say the word "hello"
'''

import sys

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps

def run(sdk_conn):
    '''The run method runs once Cozmo is connected.'''
    robot = sdk_conn.wait_for_robot()

    robot.set_all_backpack_lights(cozmo.lights.red_light)

    robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceLoseSession).wait_for_completed()

    # make cozmo reverse 100mm (negative distance == reverse)
    robot.drive_straight(distance=distance_mm(-100),
                         speed=speed_mmps(50)).wait_for_completed()

    robot.play_anim_trigger(cozmo.anim.Triggers.ReactToCliff).wait_for_completed()

    robot.say_text("Hello").wait_for_completed()


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
