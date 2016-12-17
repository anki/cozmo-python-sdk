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

'''Make Cozmo drive towards his charger.

The script shows an example of accessing the charger object from
Cozmo's world, and driving towards it.
'''

import asyncio
import sys
import time

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps
from cozmo.util import Pose, Position, Rotation

def drive_to_charger(robot):
    '''The core of the drive_to_charger program'''

    # If the robot was on the charger, drive them forward and clear of the charger
    if robot.is_on_charger:
        # drive off the charger
        robot.drive_off_charger_contacts().wait_for_completed()
        robot.drive_straight(distance_mm(130), speed_mmps(50)).wait_for_completed()
        # Start moving the lift down
        robot.move_lift(-3)
        # turn around to look at the charger
        robot.turn_in_place(degrees(180)).wait_for_completed()
        # Tilt the head to be level
        robot.set_head_angle(degrees(0)).wait_for_completed()
        # wait half a second to ensure Cozmo has seen the charger
        time.sleep(0.5)
        # drive backwards away from the charger
        robot.drive_straight(distance_mm(-60), speed_mmps(50)).wait_for_completed()

    # try to find the charger
    charger = None

    # see if Cozmo already knows where the charger is
    if robot.world.charger:
        if robot.world.charger.pose.origin_id == robot.pose.origin_id:
            print("Cozmo already knows where the charger is!")
            charger = robot.world.charger
        else:
            # Cozmo knows about the charger, but the pose is not based on the
            # same origin as the robot (e.g. the robot was moved since seeing
            # the charger) so try to look for the charger first
            pass

    if not charger:
        # Tell Cozmo to look around for the charger
        look_around = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
        try:
            charger = robot.world.wait_for_observed_charger(timeout=30)
            print("Found charger: %s" % charger)
        except asyncio.TimeoutError:
            print("Didn't see the charger")
        finally:
            # whether we find it or not, we want to stop the behavior
            look_around.stop()

    if charger:
        # In case it is near the dock, lift its arm a bit to not get blocked while rotating
        # print("Cozmo's pose: %s"  % robot.pose_angle)
        robot.set_lift_height(0.5,0.5,0.5,0.1).wait_for_completed()
        # Here we should modify the charger pose to not try to climb it before we rotate
        # TODO
        
        robot.go_to_pose(charger.pose).wait_for_completed()
        # Attempt to rotate 180 to prepare to go backwards
        robot.turn_in_place(degrees(180)).wait_for_completed()
        # Attempt to drive backwards
        action = robot.drive_straight(distance_mm(-100), speed_mmps(80)).wait_for_completed()
        # Here we assume that it is straight on the direction. Probably a better way to do it 
        # is to check after 2-3 tries if it did not get on the charger, to retry to auto_dock
        while robot.is_on_charger == False:
            action = robot.drive_straight(distance_mm(-10), speed_mmps(60)).wait_for_completed()

        robot.set_lift_height(0,0.5,0.5,0.1).wait_for_completed()
        print("Completed action: auto docking")
        
def run(sdk_conn):
    '''The run method runs once the Cozmo SDK is connected.'''
    robot = sdk_conn.wait_for_robot()

    try:
        drive_to_charger(robot)

    except KeyboardInterrupt:
        print("")
        print("Exit requested by user")


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False  # Cozmo can stay on charger for now
    try:
        cozmo.connect_with_tkviewer(run, force_on_top=True)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
