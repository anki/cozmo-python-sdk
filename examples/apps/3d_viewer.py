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

'''3d Viewer example, with remote control.

This is an example of how you can use the 3D viewer with a program, and the
3D viewer and controls will work automatically.
'''

import asyncio

import cozmo


async def cozmo_program(robot: cozmo.robot.Robot):
    while True:
        await asyncio.sleep(1)


cozmo.robot.Robot.drive_off_charger_on_connect = False
cozmo.run_program(cozmo_program, use_3d_viewer=True, use_viewer=True)



