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

"""Desk Security Guard Tutorial - Example 4 - face detection

Add event handlers to be notified of faces appearing and disappearing from view.
"""

import asyncio
import cozmo


def face_appeared(evt, face: cozmo.faces.Face, **kwargs):
    print("Face %s '%s' appeared" % (face.face_id, face.name))


def face_disappeared(evt, face: cozmo.faces.Face, **kwargs):
    print("Face %s '%s' disappeared" % (face.face_id, face.name))


async def cozmo_program(robot: cozmo.robot.Robot):
    robot.add_event_handler(cozmo.faces.EvtFaceAppeared, face_appeared)
    robot.add_event_handler(cozmo.faces.EvtFaceDisappeared, face_disappeared)
    # Keep the program running for 30 seconds
    # Note: must use `await asyncio.sleep()`, not time.sleep(), to allow other code to keep running
    await asyncio.sleep(30)


cozmo.run_program(cozmo_program)
