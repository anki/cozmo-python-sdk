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

'''Cube Roller asynchronous example

Cozmo will wait for the user to places a cube in front of him.  He will 
then approach the cube, and either roll it over or complain if the cube
isn't the one he wanted.

This example is meant to show an example usage of the high level
dock_with_cube and roll_cube actions, within an asynchronous context.
'''

import asyncio
import sys

import cozmo
from cozmo.objects import LightCube1Id, LightCube2Id, LightCube3Id
from cozmo.util import distance_mm, speed_mmps

async def cozmo_program(robot: cozmo.robot.Robot):
    '''The async equivalent of 01_cube_blinker_sync.

    The usage of ``async def`` makes the cozmo_program method a coroutine.
    Within a coroutine, ``await`` can be used. With ``await``, the statement
    blocks until the request being waited for has completed. Meanwhile
    the event loop continues in the background.

    For instance, the statement
    ``await robot.world.wait_for_observed_light_cube()``
    blocks until Cozmo observes a light cube.

    For more information, see
    https://docs.python.org/3/library/asyncio-task.html
    '''

    while True:

        ''' Cozmo will first promt the user with a verbal request.
        We are storing this action, so that we may cancel it later.
        We are running this action in parallel, so that he may start 
        looking for the cube while he is still talking.
        '''
        speakAction = robot.say_text("show me a cube", in_parallel=True)

        ''' Cozmo waits until he sees a light cube.  When he does,
        we cancel his speaking action if it is still running so that
        he will respond immediately.
        '''
        cube = await robot.world.wait_for_observed_light_cube()
        if speakAction.is_running: speakAction.abort()

        ''' In this example Cozmo is arbitrarily biased against
        the first light cube (The one that looks like a paperclip)
        '''
        if cube.object_id == LightCube1Id:

            ''' If he has seen the paperclip, he will approach it,
            then he will back up 60mm, and alert you of his dissaproval

            These actions are all specificially awaiting a wait_for_completed
            so that they will be run one after another in this asynchronous
            context, as opposed to how we spoke and looked for cubes 
            simultaneously earlier.
            '''
            await robot.dock_with_cube( cube ).wait_for_completed()

            await robot.drive_straight(distance_mm(-60), speed=speed_mmps(100)).wait_for_completed()
            await robot.say_text("not that one").wait_for_completed()
        else:
            ''' for any other cube, he will approach the cube and roll it.
            we are including the optional check_for_object_on_top parameter
            which will cause cozmo to ignore this cube if it is in a stack.

            The roll behavior can be perfomed on a stack, but may have less
            reliable results.
            '''
            await robot.roll_cube( cube, check_for_object_on_top=True ).wait_for_completed()

        ''' regardless of what he does, cozmo will wait 2 seconds before
        repeating this process.  This will give us time to move the cubes,
        and prevent the program from getting overwhelmed if no time has
        passed.  This can occur if he is staring at a stack of cubes, which
        will cancel his first spoken request, and skip the roll_cube action.
        '''
        await asyncio.sleep(2.0)

cozmo.run_program(cozmo_program)
