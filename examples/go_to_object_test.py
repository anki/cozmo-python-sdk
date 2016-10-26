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

'''Tell Cozmo to find a cube, and then drive up to it

This is a test / example usage of the robot.go_to_object call which creates a
GoToObject action, that can be used to drive within a given distance of an
object (e.g. a LightCube).
'''

import asyncio
import sys

import cozmo
from cozmo.util import degrees, distance_mm


def go_to_object_test(robot):
    '''The core of the go to object test program'''

    # Move lift down and tilt the head up
    robot.move_lift(-3)
    robot.set_head_angle(degrees(0)).wait_for_completed()

    # look around and try to find a cube
    look_around = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

    cube = None

    try:
        cube = robot.world.wait_for_observed_light_cube(timeout=30)
        print("Found cube: %s" % cube)
    except asyncio.TimeoutError:
        print("Didn't find a cube")
    finally:
        # whether we find it or not, we want to stop the behavior
        look_around.stop()

    if cube:
        # Drive to 70mm away from the cube (much closer and Cozmo
        # will likely hit the cube) and then stop.
        action = robot.go_to_object(cube, distance_mm(70.0))
        action.wait_for_completed()
        print("Completed action: result = %s" % action)
        print("Done.")


def run(sdk_conn):
    '''The run method runs once Cozmo is connected.'''
    robot = sdk_conn.wait_for_robot()

    try:
        go_to_object_test(robot)

    except KeyboardInterrupt:
        print("")
        print("Exit requested by user")

if __name__ == '__main__':
    cozmo.setup_basic_logging()
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
