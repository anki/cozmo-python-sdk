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

'''
    Advanced example recreating Quick Tap, a game to play with Cozmo within the normal app.

'''
import cozmo
import asyncio
import random
from cozmo.util import degrees, radians, distance_mm, speed_mmps
from cozmo.lights import Color, Light

yellow_light = Light(Color(name='yellow', rgb=(255,255,0)))

class QuickTapGame:
    def __init__(self,robot: cozmo.robot.Robot):
        self.robot = robot
        self.cubes = [self.robot.world.get_light_cube(cozmo.objects.LightCube1Id),self.robot.world.get_light_cube(cozmo.objects.LightCube2Id),self.robot.world.get_light_cube(cozmo.objects.LightCube3Id)]
        self.cozmo_cube = None
        self.player_cube = None
        self.countdown_cube = None

        self.game_state='choose_cubes'

        self.number_to_get_to_win = 5

        self.game_difficulty = None
        self.cozmo_accuracy_rate = 0.75
        self.different_buzzer_color_rate = 0.25
        self.red_buzzer_rate = 0.25
        self.buzzer_display_type = None

        self.player_score = 0
        self.cozmo_score = 0
        self.player_has_tapped = False

        robot.add_event_handler(cozmo.anim.EvtAnimationCompleted, self.on_anim_completed)
        robot.add_event_handler(cozmo.objects.EvtObjectTapped, self.on_cube_tap)

    async def run(self):
        await self.robot.set_lift_height(0).wait_for_completed()
        await self.cube_setup()
        self.game_state='game'
        while max(self.player_score, self.cozmo_score)<self.number_to_get_to_win:
            await self.new_tap_round()
            await asyncio.sleep(1) #allow time for the scores to be updated in the on_anim_complete method
        self.report_winner()

    async def cube_setup(self):
        await self.select_cozmo_cube()
        await self.select_player_cube()

    async def select_cozmo_cube(self):
        self.cozmo_cube = await self.robot.world.wait_for_observed_light_cube()
        self.cozmo_cube.set_lights(cozmo.lights.white_light)
        await asyncio.sleep(2)
        self.cozmo_cube.start_light_chaser()
        await self.robot.set_lift_height(1.0).wait_for_completed()
        await self.robot.go_to_object(self.cozmo_cube,distance_mm(40)).wait_for_completed()
        await self.robot.play_anim_trigger(cozmo.anim.Triggers.OnSpeedtapTap).wait_for_completed()
        self.cozmo_cube.stop_light_chaser()

    async def select_player_cube(self):
        for cube in self.cubes:
            if cube.object_id != self.cozmo_cube.object_id:
                cube.start_light_chaser()
        await self.robot.world.wait_for(cozmo.objects.EvtObjectTapped)
        self.player_cube.stop_light_chaser()
        for cube in self.cubes:
            if cube.object_id != self.cozmo_cube.object_id and cube.object_id != self.player_cube.object_id:
                self.countdown_cube = cube
                self.countdown_cube.stop_light_chaser()

    async def new_tap_round(self):    
        await self.robot.set_lift_height(1.0).wait_for_completed()
        await self.start_countdown()
        await self.start_the_race()
        self.player_has_tapped = False
        await self.determine_cozmo_move()

    async def start_countdown(self):
        self.countdown_cube.set_light_corners(cozmo.lights.green_light,cozmo.lights.green_light,cozmo.lights.green_light,cozmo.lights.green_light)
        await asyncio.sleep(.5)
        self.countdown_cube.set_light_corners(cozmo.lights.green_light,cozmo.lights.green_light,cozmo.lights.green_light,cozmo.lights.off_light)
        await asyncio.sleep(.5)
        self.countdown_cube.set_light_corners(cozmo.lights.green_light,cozmo.lights.green_light,cozmo.lights.off_light,cozmo.lights.off_light)
        await asyncio.sleep(.5)
        self.countdown_cube.set_light_corners(cozmo.lights.green_light,cozmo.lights.off_light,cozmo.lights.off_light,cozmo.lights.off_light)
        await asyncio.sleep(.5)
        self.countdown_cube.set_light_corners(cozmo.lights.off_light,cozmo.lights.off_light,cozmo.lights.off_light,cozmo.lights.off_light)
        await asyncio.sleep(.5)

    async def start_the_race(self):
        self.countdown_cube.set_lights(cozmo.lights.off_light)
        self.turn_off_buzzer_cubes()
        cube_light_delay = random.random()*4
        await asyncio.sleep(cube_light_delay)
        self.determine_buzzer_display()
        self.set_buzzer_lights()

    def determine_buzzer_display(self):
        probability_red = random.random()
        if probability_red < self.red_buzzer_rate:
            self.buzzer_display_type='red'
        else:
            probability_different_colors = random.random()
            if probability_different_colors < self.different_buzzer_color_rate:
                self.buzzer_display_type='different_colors'
            else:
                self.buzzer_display_type='same_colors'

    def set_buzzer_lights(self):
        if self.buzzer_display_type=='red':
            self.turn_on_buzzer_cubes_red()
        elif self.buzzer_display_type=='different_colors':
            self.turn_on_buzzer_cubes_different()
        elif self.buzzer_display_type=='same_colors':
            self.turn_on_buzzer_cubes_same()

    async def determine_cozmo_move(self):
        probability_cozmo_right = random.random()
        if probability_cozmo_right < self.cozmo_accuracy_rate:
            if self.buzzer_display_type=='same_colors':
                await self.cozmo_tap()
            else:
                await self.cozmo_not_tap()
        else:
            if self.buzzer_display_type=='red' or self.buzzer_display_type=='different_colors':
                await self.cozmo_tap()
            else:
                await self.cozmo_not_tap()

    async def cozmo_tap(self):
        cozmo_tap_delay = random.random()*.5
        await asyncio.sleep(cozmo_tap_delay)
        await self.robot.play_anim_trigger(cozmo.anim.Triggers.OnSpeedtapTap).wait_for_completed()

    async def cozmo_not_tap(self):
        cozmo_tap_delay = random.random()*.5
        probability_fakeout = random.random()
        await asyncio.sleep(cozmo_tap_delay)
        if probability_fakeout < 0.5:
            await self.robot.play_anim_trigger(cozmo.anim.Triggers.OnSpeedtapFakeout).wait_for_completed()
        else:
            await self.robot.play_anim_trigger(cozmo.anim.Triggers.OnSpeedtapIdle).wait_for_completed()

    async def on_cube_tap(self,evt,**kwargs):
        if self.game_state=='choose_cubes':
            if kwargs['obj'].object_id != self.cozmo_cube.object_id:
                self.player_cube = kwargs['obj']
                self.player_cube.set_lights(cozmo.lights.off_light)
        elif self.game_state=='game':
            if kwargs['obj'].object_id == self.player_cube.object_id:
                self.player_has_tapped = True

    async def on_anim_completed(self,evt,**kwargs):
        if self.game_state=='game':
            if self.buzzer_display_type=='same_colors':
                if self.player_has_tapped:
                    print("player wins the round")
                    self.player_score+=1
                else:
                    print("cozmo wins the round")
                    self.cozmo_score+=1
            elif self.buzzer_display_type=='different_colors' or self.buzzer_display_type=='red':
                if self.player_has_tapped:
                    print("cozmo wins the round")
                    self.cozmo_score+=1
            print("player score: {}".format(self.player_score))
            print("cozmo score: {}".format(self.cozmo_score))

    def turn_on_buzzer_cubes_same(self):
        self.player_cube.set_lights(cozmo.lights.white_light)
        self.cozmo_cube.set_lights(cozmo.lights.white_light)

    def turn_on_buzzer_cubes_different(self):
        self.player_cube.set_lights(cozmo.lights.green_light)
        self.cozmo_cube.set_lights(cozmo.lights.red_light)

    def turn_on_buzzer_cubes_red(self):
        self.player_cube.set_lights(cozmo.lights.red_light)
        self.cozmo_cube.set_lights(cozmo.lights.red_light)

    def turn_off_buzzer_cubes(self):
        self.player_cube.set_lights(cozmo.lights.off_light)
        self.cozmo_cube.set_lights(cozmo.lights.off_light)

    def report_winner(self):
        print("You won {} rounds".format(self.player_score))
        print("Cozmo won {} rounds".format(self.cozmo_score))
        print("{} win{}".format("Cozmo" if self.cozmo_score>self.player_score else "You", "s" if self.cozmo_score>self.player_score else ""))

class BlinkyCube(cozmo.objects.LightCube):

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._chaser = None

    def start_light_chaser(self):
        if self._chaser:
            raise ValueError("Light chaser already running")
        async def _chaser():
            rainbow_colors = [cozmo.lights.blue_light,cozmo.lights.red_light,cozmo.lights.green_light,cozmo.lights.white_light]
            while True:
                for i in range(4):
                    self.set_light_corners(*rainbow_colors)
                    await asyncio.sleep(0.1, loop=self._loop)
                    light = rainbow_colors.pop(0)
                    rainbow_colors.append(light)
        self._chaser = asyncio.ensure_future(_chaser(), loop=self._loop)

    def stop_light_chaser(self):
        if self._chaser:
            self._chaser.cancel()
            self._chaser = None
        self.set_lights_off()

cozmo.world.World.light_cube_factory = BlinkyCube

async def cozmo_program(robot: cozmo.robot.Robot):
    game = QuickTapGame(robot)
    await game.run()

cozmo.run_program(cozmo_program)