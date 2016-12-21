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

'''Drive Cozmo's wheels, lift and head motors directly

This is an example of how you can also have low-level control of Cozmo's motors
(wheels, lift and head) for fine-grained control and ease of controlling
multiple things at once.
'''

import time

import cozmo


def cozmo_program(robot: cozmo.robot.Robot):
    # Tell the head motor to start lowering the head (at 5 radians per second)
    robot.move_head(-5)
    # Tell the lift motor to start lowering the lift (at 5 radians per second)
    robot.move_lift(-5)
    # Tell Cozmo to drive the left wheel at 25 mmps (millimeters per second),
    # and the right wheel at 50 mmps (so Cozmo will drive Forwards while also
    # turning to the left
    robot.drive_wheels(25, 50)

    # wait for 3 seconds (the head, lift and wheels will move while we wait)
    time.sleep(3)

    # Tell the head motor to start raising the head (at 5 radians per second)
    robot.move_head(5)
    # Tell the lift motor to start raising the lift (at 5 radians per second)
    robot.move_lift(5)
    # Tell Cozmo to drive the left wheel at 50 mmps (millimeters per second),
    # and the right wheel at -50 mmps (so Cozmo will turn in-place to the right)
    robot.drive_wheels(50, -50)

    # wait for 3 seconds (the head, lift and wheels will move while we wait)
    time.sleep(3)


cozmo.run_program(cozmo_program)
