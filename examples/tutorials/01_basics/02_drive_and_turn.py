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

'''Drive And Turn

Make Cozmo drive forwards and then turn 90 degrees to the left.
'''

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps


def cozmo_program(robot: cozmo.robot.Robot):
    # Drive forwards for 150 millimeters at 50 millimeters-per-second.
    robot.drive_straight(distance_mm(150), speed_mmps(50)).wait_for_completed()

    # Turn 90 degrees to the left.
    # Note: To turn to the right, just use a negative number.
    robot.turn_in_place(degrees(90)).wait_for_completed()


cozmo.run_program(cozmo_program)
