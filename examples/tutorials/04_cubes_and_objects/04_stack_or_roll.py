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

'''Make Cozmo perform different actions based on the number of Cubes he finds.

This script shows off simple decision making.
It tells Cozmo to look around, and then wait until he sees a certain amount of objects.
Based on how many object he sees before he times out, he will do different actions.
0-> be angry
1-> roll block (the block must not be face up)
2-> stack blocks (the blocks must all be face up)
'''

import cozmo


def cozmo_program(robot: cozmo.robot.Robot):
    lookaround = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

    cubes = robot.world.wait_until_observe_num_objects(num=2, object_type=cozmo.objects.LightCube, timeout=10)

    print("Found %s cubes" % len(cubes))

    lookaround.stop()

    if len(cubes) == 0:
        robot.play_anim_trigger(cozmo.anim.Triggers.MajorFail).wait_for_completed()
    elif len(cubes) == 1:
        robot.run_timed_behavior(cozmo.behavior.BehaviorTypes.RollBlock, active_time=60)
    else:
        robot.run_timed_behavior(cozmo.behavior.BehaviorTypes.StackBlocks, active_time=60)


cozmo.run_program(cozmo_program)
