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

'''Cozmo the Desk Security Guard.

Cozmo patrols your desk, looks out for unknown faces, and reports them to you.
'''

import asyncio
from random import randint
import sys
import time

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps

#: The name that the owner's face is enrolled as (i.e. your username in the app)
#: When that face is seen, Cozmo will assume no other faces currently seen are intruders
OWNER_FACE_ENROLL_NAME = ""


if OWNER_FACE_ENROLL_NAME == "":
    sys.exit("You must fill in OWNER_FACE_ENROLL_NAME")


class DeskSecurityGuard:
    '''Container for Security Guard status'''

    def __init__(self):
        self.owner_name = OWNER_FACE_ENROLL_NAME

        self.is_armed = True

        self.time_first_observed_intruder = None
        self.time_last_observed_intruder = None

        self.time_first_observed_owner = None
        self.time_last_observed_owner = None

        self.time_last_suspicious = None
        self.time_last_uploaded_photo = None
        self.time_last_announced_intruder = None
        self.time_last_pounced_at_intruder = None
        self.time_last_announced_owner = None

    def is_investigating_intruder(self):
        '''Has an unknown face recently been seen?'''
        return self.time_first_observed_intruder is not None

    def has_confirmed_intruder(self):
        '''The robot has seen an intruder for long enough that it's pretty sure it's not the owner.'''
        if self.time_first_observed_intruder:
            elapsed_time = time.time() - self.time_first_observed_intruder
            return elapsed_time > 2.0
        return False


def did_occur_recently(event_time, max_elapsed_time):
    '''Did event_time occur and was it within the last max_elapsed_time seconds?'''
    if event_time is None:
        return False
    elapsed_time = time.time() - event_time
    return elapsed_time < max_elapsed_time


async def check_for_intruder(robot, dsg:DeskSecurityGuard):
    ''''''

    # Check which faces can be seen, and if any are the owner or an intruder

    owner_face = None
    intruder_face = None
    for visible_face in robot.world.visible_faces:
        if visible_face.name.lower() == dsg.owner_name.lower():
            if owner_face:
                print("Multiple faces with name %s seen - %s and %s!" %
                      (dsg.owner_name, owner_face, visible_face))
            owner_face = visible_face
        else:
            # just use the first intruder seen
            if not intruder_face:
                intruder_face = visible_face

    # Update times first/last seen owner or an intruder

    if owner_face:
        dsg.time_last_observed_owner = owner_face.last_observed_time
        if dsg.time_first_observed_owner is None:
            dsg.time_first_observed_owner = dsg.time_last_observed_owner

    if intruder_face:
        if dsg.time_last_observed_intruder is None or \
                        intruder_face.last_observed_time > dsg.time_last_observed_intruder:
            dsg.time_last_observed_intruder = intruder_face.last_observed_time

        if dsg.time_first_observed_intruder is None:
            dsg.time_first_observed_intruder = dsg.time_last_observed_intruder

    # Check if there's anything to investigate

    can_see_owner = did_occur_recently(dsg.time_last_observed_owner, 1.0)
    can_see_intruders = did_occur_recently(dsg.time_last_observed_intruder, 1.0)
    if not dsg.is_armed:
        can_see_intruders = False
    if not can_see_intruders:
        dsg.time_first_observed_intruder = None

    if can_see_owner:

        # If robot can see the owner then look at and greet them occasionally

        robot.set_all_backpack_lights(cozmo.lights.green_light)
        if not did_occur_recently(dsg.time_last_announced_owner, 60.0):
            await robot.play_anim_trigger(cozmo.anim.Triggers.NamedFaceInitialGreeting).wait_for_completed()
            dsg.time_last_announced_owner = time.time()
        elif owner_face:
            await robot.turn_towards_face(owner_face).wait_for_completed()
    elif can_see_intruders:

        # Don't react unless this is a confirmed intruder

        is_confirmed_intruder = dsg.has_confirmed_intruder()
        if is_confirmed_intruder:
            # Definitely an intruder - turn backpack red to indicate
            robot.set_all_backpack_lights(cozmo.lights.red_light)

            # Sound an alarm (every X seconds)
            if not did_occur_recently(dsg.time_last_announced_intruder, 10):
                await robot.say_text("Intruder Alert").wait_for_completed()
                dsg.time_last_announced_intruder = time.time()

            # Pounce at intruder (every X seconds)
            if not did_occur_recently(dsg.time_last_pounced_at_intruder, 10.0):
                await robot.play_anim_trigger(cozmo.anim.Triggers.CubePouncePounceNormal).wait_for_completed()
                dsg.time_last_pounced_at_intruder = time.time()

            # Turn towards the intruder to keep them in view
            if intruder_face:
                await robot.turn_towards_face(intruder_face).wait_for_completed()
        else:
            # Possibly an intruder - turn backpack blue to indicate, and play
            # suspicious animation (if not played recently)

            robot.set_all_backpack_lights(cozmo.lights.blue_light)
            if not did_occur_recently(dsg.time_last_suspicious, 10.0):
                await robot.play_anim_trigger(cozmo.anim.Triggers.HikingInterestingEdgeThought).wait_for_completed()
                dsg.time_last_suspicious = time.time()
            elif intruder_face:
                # turn robot towards intruder face slightly to get a better look at them
                await robot.turn_towards_face(intruder_face).wait_for_completed()
    else:
        robot.set_backpack_lights_off()


async def desk_security_guard(robot):
    '''The core of the desk_security_guard program'''

    # Turn on image receiving by the camera
    robot.camera.image_stream_enabled = True

    # Create our security guard
    dsg = DeskSecurityGuard()

    # Make sure Cozmo is clear of the charger
    if robot.is_on_charger:
        # Drive fully clear of charger (not just off the contacts)
        await robot.drive_off_charger_contacts().wait_for_completed()
        await robot.drive_straight(distance_mm(150), speed_mmps(50)).wait_for_completed()

    # Tilt head up to look for people
    await robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

    initial_pose_angle = robot.pose_angle

    patrol_offset = 0  # middle
    max_pose_angle = 45  # offset from initial pose_angle (up to +45 or -45 from this)

    # Time to wait between each turn and patrol, in seconds
    time_between_turns = 2.5
    time_between_patrols = 20

    time_for_next_turn = time.time() + time_between_turns
    time_for_next_patrol = time.time() + time_between_patrols

    while True:

        # Turn head every few seconds to cover a wider field of view
        # Only do this if not currently investigating an intruder

        if (time.time() > time_for_next_turn) and not dsg.is_investigating_intruder():
            # pick a random amount to turn
            angle_to_turn = randint(10,40)

            # 50% chance of turning in either direction
            if randint(0,1) > 0:
                angle_to_turn = -angle_to_turn

            # Clamp the amount to turn

            face_angle = (robot.pose_angle - initial_pose_angle).degrees

            face_angle += angle_to_turn
            if face_angle > max_pose_angle:
                angle_to_turn -= (face_angle - max_pose_angle)
            elif face_angle < -max_pose_angle:
                angle_to_turn -= (face_angle + max_pose_angle)

            # Turn left/right
            await robot.turn_in_place(degrees(angle_to_turn)).wait_for_completed()

            # Tilt head up/down slightly
            await robot.set_head_angle(degrees(randint(30,44))).wait_for_completed()

            # Queue up the next time to look around
            time_for_next_turn = time.time() + time_between_turns

        # Every now and again patrol left and right between 3 patrol points

        if (time.time() > time_for_next_patrol) and not dsg.is_investigating_intruder():

            # Check which way robot is facing vs initial pose, pick a new patrol point

            face_angle = (robot.pose_angle - initial_pose_angle).degrees
            drive_right = (patrol_offset < 0) or ((patrol_offset == 0) and (face_angle > 0))

            # Turn to face the new patrol point

            if drive_right:
                await robot.turn_in_place(degrees(90 - face_angle)).wait_for_completed()
                patrol_offset += 1
            else:
                await robot.turn_in_place(degrees(-90 - face_angle)).wait_for_completed()
                patrol_offset -= 1

            # Drive to the patrol point, playing animations along the way

            await robot.drive_wheels(20, 20)
            for i in range(1,4):
                await robot.play_anim("anim_hiking_driving_loop_0" + str(i)).wait_for_completed()

            # Stop driving

            robot.stop_all_motors()

            # Turn to face forwards again

            face_angle = (robot.pose_angle - initial_pose_angle).degrees
            if face_angle > 0:
                await robot.turn_in_place(degrees(-90)).wait_for_completed()
            else:
                await robot.turn_in_place(degrees(90)).wait_for_completed()

            # Queue up the next time to patrol
            time_for_next_patrol = time.time() + time_between_patrols

        # look for intruders

        await check_for_intruder(robot, dsg)

        # Sleep to allow other things to run

        await asyncio.sleep(0.05)


async def run(sdk_conn):
    '''The run method runs once the Cozmo SDK is connected.'''
    robot = await sdk_conn.wait_for_robot()

    try:
        await desk_security_guard(robot)

    except KeyboardInterrupt:
        print("")
        print("Exit requested by user")


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False  # Stay on charger until init
    try:
        cozmo.connect_with_tkviewer(run, force_on_top=True)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)

