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

'''Make Cozmo stack Cubes.

This script is meant to show off how easy it is to do high level robot actions.
Cozmo will wait until he sees two Cubes, and then will pick up one and place it on the other.
He will pick up the first one he sees, and place it on the second one.
'''

import sys

import cozmo

def run(sdk_conn):
    '''The run method runs once Cozmo is connected.'''
    robot = sdk_conn.wait_for_robot()

    lookaround = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

    cubes = robot.world.wait_until_observe_num_objects(num=2, object_type=cozmo.objects.LightCube, timeout=60)

    lookaround.stop()

    if len(cubes) < 2:
        print("Error: need 2 Cubes but only found", len(cubes), "Cube(s)")
    else:
        current_action = robot.pickup_object(cubes[0])
        current_action.wait_for_completed()
        if current_action.has_failed:
            code, reason = current_action.failure_reason
            print("Pickup Cube failed: code=%s reason=%s" % (code, reason))

        current_action = robot.place_on_object(cubes[1])
        current_action.wait_for_completed()
        if current_action.has_failed:
            code, reason = current_action.failure_reason
            print("Place On Cube failed: code=%s reason=%s" % (code, reason))

if __name__ == '__main__':
    cozmo.setup_basic_logging()
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
