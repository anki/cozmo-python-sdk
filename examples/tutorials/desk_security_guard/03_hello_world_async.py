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

"""Desk Security Guard Tutorial - Example 3 - async

To use asyncio, and run cozmo_program as a coroutine:
1. Mark the method as async.
2. “await” all async methods called from there
   (anything that takes time to execute, or waits,
    should be async).
"""

import cozmo


async def cozmo_program(robot: cozmo.robot.Robot):
    action = robot.say_text("Hello World")
    await action.wait_for_completed()


cozmo.run_program(cozmo_program)
