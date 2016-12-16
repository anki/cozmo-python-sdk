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

'''Make Cozmo sing Do Re Mi.

Make Cozmo "sing" the scales.
This is a small extension of the 03_count.py example.
'''

import cozmo
from cozmo.util import degrees


def cozmo_program(robot: cozmo.robot.Robot):
    # scales is a list of the words for Cozmo to sing
    scales = ["Doe", "Ray", "Mi", "Fa", "So", "La", "Ti", "Doe"]

    # Find voice_pitch_delta value that will range the pitch from -1 to 1 over all of the scales
    voice_pitch = -1.0
    voice_pitch_delta = 2.0 / (len(scales) - 1)

    # Move head and lift down to the bottom, and wait until that's achieved
    robot.move_head(-5) # start moving head down so it mostly happens in parallel with lift
    robot.set_lift_height(0.0).wait_for_completed()
    robot.set_head_angle(degrees(-25.0)).wait_for_completed()

    # Start slowly raising lift and head
    robot.move_lift(0.15)
    robot.move_head(0.15)

    # "Sing" each note of the scale at increasingly high pitch
    for note in scales:
        robot.say_text(note, voice_pitch=voice_pitch, duration_scalar=0.3).wait_for_completed()
        voice_pitch += voice_pitch_delta


cozmo.run_program(cozmo_program)
