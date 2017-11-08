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

"""Desk Security Guard Tutorial - Example 10 - Guard a 90 degree arc."""

import asyncio
from random import randint

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps


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

    async def get_in_start_position(self):
        if self.robot.is_on_charger:
            # Drive fully clear of charger (not just off the contacts)
            await self.robot.drive_off_charger_contacts().wait_for_completed()
            await self.robot.drive_straight(distance_mm(150),
                                            speed_mmps(50)).wait_for_completed()

    async def run(self):
        await self.get_in_start_position()

        initial_pose_angle = self.robot.pose_angle
        max_offset_angle = 45  # max offset in degrees: Either +ve (left), or -ve (right)
        turn_scalar = 1  # 1 will increase the offset (turn left), -1 will do the opposite

        for _ in range(12):
            # pick a random amount to turn in the current direction
            angle_to_turn = turn_scalar * randint(10,40)

            # Find how far robot is already turned, and calculate the new offset
            current_angle_offset = (self.robot.pose_angle - initial_pose_angle).degrees
            new_angle_offset = current_angle_offset + angle_to_turn

            # Clamp the turn to the desired offsets
            if new_angle_offset > max_offset_angle:
                angle_to_turn = max_offset_angle - current_angle_offset
                turn_scalar = -1  # turn the other direction next time
            elif new_angle_offset < -max_offset_angle:
                angle_to_turn = -max_offset_angle - current_angle_offset
                turn_scalar = 1  # turn the other direction next time

            # Tilt head up/down slightly each time
            random_head_angle = degrees(randint(30, 44))
            action1 = self.robot.set_head_angle(random_head_angle, in_parallel=True)
            action2 = self.robot.turn_in_place(degrees(angle_to_turn), in_parallel=True)
            # Wait for both actions to complete
            await action1.wait_for_completed()
            await action2.wait_for_completed()
            # Force Cozmo to wait for a couple of seconds to improve chance of seeing something
            await asyncio.sleep(2)


async def cozmo_program(robot: cozmo.robot.Robot):
    desk_guard = DeskGuard(robot, "Wez")
    await desk_guard.run()


# Leave Cozmo on his charger at connection, so we can handle it ourselves
cozmo.robot.Robot.drive_off_charger_on_connect = False
cozmo.run_program(cozmo_program)
