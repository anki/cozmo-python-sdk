#!/usr/bin/env python3

# Copyright (c) 2017 Anki, Inc.
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

'''Play Sounds

Play a one-off sound on the device, then play one of the Tiny Orchestra loops.
'''

import time

import cozmo

def cozmo_program(robot: cozmo.robot.Robot):
    # Play a sound that ends on its own
    robot.play_audio(cozmo.audio.AudioEvents.SfxGameWin)

    # Start the tiny orchestra system
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraInit)

    # turn on the bass_mode_1 channel.
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraBassMode1)

    # turn on the strings_mode_3 channel after 5 seconds
    # It will play in sync with the bass regardless of the sleep duration.
    time.sleep(5.0)
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraStringsMode3)

    # Stop the tiny orchestra system after 5 seconds
    time.sleep(5.0)
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraStop)


cozmo.run_program(cozmo_program)
