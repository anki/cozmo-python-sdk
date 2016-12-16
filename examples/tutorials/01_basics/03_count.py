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

'''Count to 5

Make Cozmo count from 1 to 5
'''

import cozmo


def cozmo_program(robot: cozmo.robot.Robot):
    # A "for loop" runs for each value i in the given range - in this example
    # starting from 0, while i is less than 5 (so 0,1,2,3,4).
    for i in range(5):
        # Add 1 to the number (so that we count from 1 to 5, not 0 to 4),
        # then convert the number to a string and make Cozmo say it.
        robot.say_text(str(i+1)).wait_for_completed()


cozmo.run_program(cozmo_program)
