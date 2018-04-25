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

'''Play some animations on Cozmo

Plays animations by fetching lists of supported triggers from the robot,
and playing 2 selections of them: one random selection and one by filtering
for a name.
'''

import cozmo
import random

def cozmo_program(robot: cozmo.robot.Robot):
    # grab a list of animation triggers
    all_animation_triggers = robot.anim_triggers

    # randomly shuffle the animations
    random.shuffle(all_animation_triggers)

    # select the first three animations from the shuffled list
    triggers = 3
    chosen_triggers = all_animation_triggers[:triggers]
    print('Playing {} random animations:'.format(triggers))

    # play the three random animations one after the other, waiting for each to complete
    for trigger in chosen_triggers:
        print('Playing {}'.format(trigger.name))
        robot.play_anim_trigger(trigger).wait_for_completed()


    # grab animation triggers that have 'WinGame' in their name
    chosen_triggers = [trigger for trigger in robot.anim_triggers if 'WinGame' in trigger.name]

    # play the three random animations one after the other, waiting for each to complete
    for trigger in chosen_triggers:
        print('Playing {}'.format(trigger.name))
        robot.play_anim_trigger(trigger).wait_for_completed()

cozmo.run_program(cozmo_program)
