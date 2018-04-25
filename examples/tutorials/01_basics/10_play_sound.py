#!/usr/bin/env python3

# Copyright (c) 2018 Anki, Inc.
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

'''Play Sounds through various methods

A) Play a one-off sound on the device
B) Play a music loop which will be interrupted while playing
C) Play one of the Tiny Orchestra loops by bringing in 2 instruments one at a
    time.
'''

import time

import cozmo

def cozmo_program(robot: cozmo.robot.Robot):
    # Play a sound that ends on its own
    robot.play_audio(cozmo.audio.AudioEvents.SfxGameWin)
    time.sleep(1.0)

    # Play a sound for us to interrupt after two seconds
    # This sound "MusicStyle80S1159BpmLoop" is:
    #   - "80S" style music #"1", at "159Bpm" (beats per minute)
    #   - if the song is played repeatedly, the beginning and end
    #     line up making it possible to play in a "Loop"
    robot.play_audio(cozmo.audio.AudioEvents.MusicStyle80S1159BpmLoop)

    # Most sounds have an accompanying (name + "Stop") event to cancel it
    # before it finishes.
    time.sleep(2.0)
    robot.play_audio(cozmo.audio.AudioEvents.MusicStyle80S1159BpmLoopStop)

    # Start the tiny orchestra system.
    # By itself, the tiny orchestra system will not make any sound, but
    # allows us to turn synchronized audio channels on and off until
    # we tell it to stop.
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraInit)

    # Turn on the bass_mode_1 channel in the tiny orchestra system.
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraBassMode1)

    # After 5 seconds...
    time.sleep(5.0)

    # Turn on the strings_mode_3 channel.
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraStringsMode3)

    # After 5 seconds...
    time.sleep(5.0)

    # Stop the tiny orchestra system.
    # This will cause all tinyOrchestra music to stop playing.
    robot.play_audio(cozmo.audio.AudioEvents.MusicTinyOrchestraStop)


cozmo.run_program(cozmo_program)
