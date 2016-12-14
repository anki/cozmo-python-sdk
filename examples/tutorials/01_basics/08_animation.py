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

'''Play an animation on Cozmo

Play animations on Cozmo
'''

import cozmo


def cozmo_program(robot: cozmo.robot.Robot):
    # Play an animation via a Trigger
    robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceLoseSession).wait_for_completed()

    # Play an animation via a Name
    robot.play_anim(name="ID_pokedB").wait_for_completed()


cozmo.run_program(cozmo_program)
