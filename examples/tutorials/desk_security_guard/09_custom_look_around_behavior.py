#!/usr/bin/env python3

# Copyright (c) 2016-2017 Anki, Inc.
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

"""Desk Security Guard Tutorial - Example 9 - Create our own custom look-around behavior."""

import asyncio
import cozmo
from cozmo.util import degrees  # saves us typing cozmo.util.degrees everywhere


class DeskGuard:
    def __init__(self, robot: cozmo.robot.Robot, owner_name: str):
        self.robot = robot
        self.owner_name = owner_name
        robot.add_event_handler(cozmo.faces.EvtFaceAppeared, self.face_appeared)
        robot.add_event_handler(cozmo.faces.EvtFaceDisappeared, self.face_disappeared)
        # Note: We're no longer starting a behavior here

    def face_appeared(self, evt, face: cozmo.faces.Face, **kwargs):
        if face.name == self.owner_name:
            self.robot.play_anim_trigger(cozmo.anim.Triggers.NamedFaceInitialGreeting,
                                         in_parallel=True)
        else:
            self.robot.say_text("Intruder Alert!", in_parallel = True)

    def face_disappeared(self, evt, face: cozmo.faces.Face, **kwargs):
        print("Face %s '%s' disappeared" % (face.face_id, face.name))

    async def run(self):
        for _ in range(12):
            # Tilt head up (if necessary) while simultaneously turning 30 degrees
            action1 = self.robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE, in_parallel=True)
            action2 = self.robot.turn_in_place(degrees(30), in_parallel=True)
            # Wait for both actions to complete
            await action1.wait_for_completed()
            await action2.wait_for_completed()
            # Force Cozmo to wait for a couple of seconds to improve chance of seeing something
            await asyncio.sleep(2)


async def cozmo_program(robot: cozmo.robot.Robot):
    desk_guard = DeskGuard(robot, "Wez")
    await desk_guard.run()


cozmo.run_program(cozmo_program)
