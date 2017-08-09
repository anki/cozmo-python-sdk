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

'''Parallel Action Examples.

This script shows how to run actions in parallel instead of in sequence,
how some actions will fail to run if another action is already using that
animation track, and how you can abort individual, or all, actions.
'''

import sys
import time

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps


# load an image to display on Cozmo's face
face_image = Image.open("../../face_images/cozmosdk.png")
# resize to fit on Cozmo's face screen
face_image = face_image.resize(cozmo.oled_face.dimensions(), Image.BICUBIC)
# convert the image to the format used by the oled screen
face_image = cozmo.oled_face.convert_image_to_screen_data(face_image,
                                                          invert_image=True)


def example1_lift_head(robot: cozmo.robot.Robot):
    cozmo.logger.info("----------------------------------------")
    cozmo.logger.info("Example 1: Move Lift and Head in Parallel")
    cozmo.logger.info("First, move the lift and head down, in sequence.")
    robot.set_head_angle(cozmo.robot.MIN_HEAD_ANGLE).wait_for_completed()
    robot.set_lift_height(0.0).wait_for_completed()

    cozmo.logger.info("Now, move the lift and head back up, in parallel "
                      "- we no longer have to wait for the 1st action to complete "
                      "before starting the 2nd one because the 2nd action is in_parallel")
    action1 = robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE)
    action2 = robot.set_lift_height(1.0, in_parallel=True)
    action1.wait_for_completed()
    action2.wait_for_completed()
    cozmo.logger.info("action1 = %s", action1)
    cozmo.logger.info("action2 = %s", action2)


def example2_conflicting_actions(robot: cozmo.robot.Robot):
    cozmo.logger.info("----------------------------------------")
    cozmo.logger.info("Example 2: Conflicting actions.")
    cozmo.logger.info("Try to drive straight and turn in parallel. This is not "
          "allowed, as both actions require use of the wheels, so the 2nd action "
          "will report failure due to tracks_locked.")
    action1 = robot.drive_straight(distance_mm(50), speed_mmps(25), should_play_anim=False, in_parallel=True)
    action2 = robot.turn_in_place(degrees(90), in_parallel=True)
    action2.wait_for_completed()
    cozmo.logger.info("action2 = %s", action2)
    action1.wait_for_completed()
    cozmo.logger.info("action1 = %s", action1)


def example3_abort_one_action(robot: cozmo.robot.Robot):
    cozmo.logger.info("----------------------------------------")
    cozmo.logger.info("Example 3: Abort some parallel actions.")
    cozmo.logger.info("Start multiple parallel actions:")
    action1 = robot.set_lift_height(0.0, in_parallel=True)
    action2 = robot.set_head_angle(cozmo.robot.MIN_HEAD_ANGLE, duration=6.0, in_parallel=True)
    action3 = robot.drive_straight(distance_mm(75), speed_mmps(25), should_play_anim=False, in_parallel=True)
    action4 = robot.display_oled_face_image(face_image, 30000.0)  # Note: face image is in_parallel by default
    # Lift-lowering is aborted immediately
    action1.abort(log_abort_messages=True)
    # Head-lowering is aborted shortly afterwards
    time.sleep(0.1)
    action2.abort(log_abort_messages=True)
    # Image on Cozmo's face is aborted another 2 seconds later
    time.sleep(2)
    action4.abort(log_abort_messages=True)
    # We wait for the one remaining action to complete
    action3.wait_for_completed()
    # Only action3 should succeed (as long as Cozmo had enough space to drive)
    cozmo.logger.info("action1 = %s", action1)
    cozmo.logger.info("action2 = %s", action2)
    cozmo.logger.info("action3 = %s", action3)
    cozmo.logger.info("action4 = %s", action4)


def example4_abort_all_actions(robot: cozmo.robot.Robot):
    cozmo.logger.info("----------------------------------------")
    cozmo.logger.info("Example 4: Abort all parallel actions.")
    cozmo.logger.info("Start multiple parallel actions:")
    action1 = robot.set_lift_height(0.0, in_parallel=True, duration=6.0)
    action2 = robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE, duration=6.0, in_parallel=True)
    action3 = robot.drive_straight(distance_mm(75), speed_mmps(25), should_play_anim=False, in_parallel=True)
    action4 = robot.display_oled_face_image(face_image, 30000.0)  # Note: face image is in_parallel by default
    # wait two seconds and abort everything
    time.sleep(2)
    robot.abort_all_actions(log_abort_messages=True)
    # wait for results to come back for all actions
    robot.wait_for_all_actions_completed()
    # All actions should have aborted
    cozmo.logger.info("action1 res = %s", action1)
    cozmo.logger.info("action2 res = %s", action2)
    cozmo.logger.info("action3 res = %s", action3)
    cozmo.logger.info("action4 res = %s", action4)


def cozmo_program(robot: cozmo.robot.Robot):
    example1_lift_head(robot)
    example2_conflicting_actions(robot)
    example3_abort_one_action(robot)
    example4_abort_all_actions(robot)
    cozmo.logger.info("----------------------------------------")


cozmo.run_program(cozmo_program)
