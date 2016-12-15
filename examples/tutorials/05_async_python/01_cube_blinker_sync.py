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

'''Cube Blinker synchronous example

Cozmo first looks around for a cube. Once a cube is found,
the cube's lights blink green in a circular fashion. The
script then waits for the cube to be tapped.
'''

import asyncio
import sys

import cozmo

class BlinkyCube(cozmo.objects.LightCube):
    '''Subclass LightCube and add a light-chaser effect.'''
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._chaser = None

    def start_light_chaser(self):
        '''Cycles the lights around the cube with 1 corner lit up green,
        changing to the next corner every 0.1 seconds.
        '''
        if self._chaser:
            raise ValueError("Light chaser already running")
        async def _chaser():
            while True:
                for i in range(4):
                    cols = [cozmo.lights.off_light] * 4
                    cols[i] = cozmo.lights.green_light
                    self.set_light_corners(*cols)
                    await asyncio.sleep(0.1, loop=self._loop)
        self._chaser = asyncio.ensure_future(_chaser(), loop=self._loop)

    def stop_light_chaser(self):
        if self._chaser:
            self._chaser.cancel()
            self._chaser = None


# Make sure World knows how to instantiate the subclass
cozmo.world.World.light_cube_factory = BlinkyCube


def cozmo_program(robot: cozmo.robot.Robot):
    cube = None
    look_around = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

    try:
        cube = robot.world.wait_for_observed_light_cube(timeout=60)
    except asyncio.TimeoutError:
        print("Didn't find a cube :-(")
        return
    finally:
        look_around.stop()

    cube.start_light_chaser()
    try:
        print("Waiting for cube to be tapped")
        cube.wait_for_tap(timeout=10)
        print("Cube tapped")
    except asyncio.TimeoutError:
        print("No-one tapped our cube :-(")
    finally:
        cube.stop_light_chaser()
        cube.set_lights_off()


cozmo.run_program(cozmo_program)
