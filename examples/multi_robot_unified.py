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

'''An example of controlling two robots from within the same routine.

Each robot requires its own device to control it.
'''

import asyncio
import sys

import cozmo
from cozmo.util import degrees


async def run(sdk_conn1, sdk_conn2):
    robot1 = await sdk_conn1.wait_for_robot()
    robot2 = await sdk_conn2.wait_for_robot()

    # First have one turn left and one turn right, one after the other
    cozmo.logger.info("Turning robot 1")
    await robot1.turn_in_place(degrees(90)).wait_for_completed()
    cozmo.logger.info("Turning robot 2")
    await robot2.turn_in_place(degrees(-90)).wait_for_completed()

    # Then have them both turn back to the original position at the same time
    cozmo.logger.info("Turning both robots")
    turn1 = robot1.turn_in_place(degrees(-90))
    turn2 = robot2.turn_in_place(degrees(90))
    await turn1.wait_for_completed()
    await turn2.wait_for_completed()


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    loop = asyncio.get_event_loop()

    # Connect to both robots
    # NOTE: to connect to a specific device with a specific serial number,
    # create a connector (eg. `cozmo.IOSConnector(serial='abc')) and pass it
    # explicitly to `connect` or `connect_on_loop`
    try:
        conn1 = cozmo.connect_on_loop(loop)
        conn2 = cozmo.connect_on_loop(loop)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)

    # Run a coroutine controlling both connections
    loop.run_until_complete(run(conn1, conn2))
