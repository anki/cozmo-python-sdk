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

sys.path.append('../lib/')
import twitter_helpers as twitter_helpers
import cozmo_twitter_keys as twitter_keys


#: The twitter user (without the @ symbol) that will receive security photos, etc.
OWNER_TWITTER_USERNAME = ""

#: The name that the owner's face is enrolled as (i.e. your username in the app)
#: When that face is seen, Cozmo will assume no other faces currently seen are intruders
OWNER_FACE_ENROLL_NAME = ""


if OWNER_TWITTER_USERNAME == "":
    sys.exit("You must fill in OWNER_TWITTER_USERNAME")
if OWNER_FACE_ENROLL_NAME == "":
    sys.exit("You must fill in OWNER_FACE_ENROLL_NAME")


class TwitterStreamToAppCommunication:
    '''Class for messaging to/from SecurityGuardStreamListener

    Tweepy doesn't support asyncio, so this program must run the SecurityGuardStreamListener
    stream in its own thread. Communication is deliberately limited between the rest of the
    program and the stream to some simple signalling bools to avoid running
    into any threading issues like race conditions.
    '''
    def __init__(self):
        self.is_armed = True
        self.has_arm_request = False
        self.has_disarm_request = False


class SecurityGuardStreamListener(twitter_helpers.CozmoTweetStreamListener):
    '''React to Tweets sent to the Cozmo user, live, as they happen...

    on_tweet_from_user is called whenever the Twitter user receives a tweet.
    This allows the only the owner to enable and disable the alarm via Twitter.
    '''

    def __init__(self, twitter_api, stream_to_app_comms):
        super().__init__(None, twitter_api)
        self.stream_to_app_comms = stream_to_app_comms
        self.owner_username = OWNER_TWITTER_USERNAME

    def do_arm(self):
        '''Request security guard alerts be enabled'''
        if self.stream_to_app_comms.is_armed:
            return "Already Armed!"
        else:
            self.stream_to_app_comms.has_arm_request = True
            return "Arming!"

    def do_disarm(self):
        '''Request security guard alerts be disabled'''
        if self.stream_to_app_comms.is_armed:
            self.stream_to_app_comms.has_disarm_request = True
            return "Disarming!"
        else:
            return "Already Disarmed!"

    def get_supported_commands(self):
        '''Construct a list of all methods in this class that start with "do_" - these are commands we accept.'''
        prefix_str = "do_"
        prefix_len = len(prefix_str)
        supported_commands = []
        for func_name in dir(self.__class__):
            if func_name.startswith(prefix_str):
                supported_commands.append(func_name[prefix_len:])
        return supported_commands

    def get_command(self, command_name):
        '''Find a matching "do_" function and return it. Return None if there's no match.'''
        try:
            return getattr(self, 'do_' + command_name.lower())
        except AttributeError:
            return None

    def extract_command_from_string(self, in_string):
        '''Separate inString at each space, loop through until we find a command, and return tuple of cmd_func and cmd_args.'''

        split_string = in_string.split()

        for i in range(len(split_string)):

            cmd_func = self.get_command(split_string[i])

            if cmd_func:
                return cmd_func

        # No valid command found
        return None

    def on_tweet_from_user(self, json_data, tweet_text, from_user, is_retweet):
        '''Handle every new tweet as it appears.'''

        # ignore retweets
        if is_retweet:
            return True

        # ignore any replies from this account (otherwise it would infinite loop as soon as you reply)
        # allow other messages from this account (so you can tweet at yourself to control Cozmo if you want)

        user_me = self.twitter_api.me()
        is_from_me = (from_user.get('id') == user_me.id)

        if is_from_me and tweet_text.startswith("@"):
            # ignore replies from this account
            return

        from_user_name = from_user.get('screen_name')

        from_owner = from_user_name.lower() == self.owner_username.lower()
        if not from_owner:
            print("Ignoring tweet from non-owner user %s" % from_user_name)
            return

        tweet_id = json_data.get('id_str')

        cmd_func = self.extract_command_from_string(tweet_text)

        reply_prefix = "@" + from_user_name + " "
        if cmd_func is not None:
            result_string = cmd_func()
            if result_string:
                self.post_tweet(reply_prefix + result_string, tweet_id)
        else:
            self.post_tweet(reply_prefix + "Sorry, I don't understand; available commands are: "
                            + str(self.get_supported_commands()), tweet_id)


class DeskSecurityGuard:
    '''Container for Security Guard status'''

    def __init__(self, twitter_api):
        self.twitter_api = twitter_api
        self.owner_username = OWNER_TWITTER_USERNAME
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
        if visible_face.name == dsg.owner_name:
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
        else:
            await robot.turn_towards_face(owner_face).wait_for_completed()
    elif can_see_intruders:

        # Don't react unless this is a confirmed intruder

        is_confirmed_intruder = dsg.has_confirmed_intruder()
        if is_confirmed_intruder:
            # Definitely an intruder - turn backpack red to indicate
            robot.set_all_backpack_lights(cozmo.lights.red_light)

            # Tweet a photo (every X seconds)
            if not did_occur_recently(dsg.time_last_uploaded_photo, 15.0):
                # Tweet the image to the owner
                latest_image = robot.world.latest_image
                if latest_image is not None:
                    status_text = "@" + dsg.owner_username + " Intruder Detected"
                    media_ids = twitter_helpers.upload_images(dsg.twitter_api, [latest_image.raw_image])
                    posted_image = twitter_helpers.post_tweet(dsg.twitter_api, status_text, media_ids=media_ids)
                    if posted_image:
                        dsg.time_last_uploaded_photo = time.time()
                    else:
                        print("Failed to tweet photo of intruder!")
                else:
                    print("No camera image available to tweet!")

            # Sound an alarm (every X seconds)
            if not did_occur_recently(dsg.time_last_announced_intruder, 10):
                await robot.say_text("Intruder Alert").wait_for_completed()
                dsg.time_last_announced_intruder = time.time()

            # Pounce at intruder (every X seconds)
            if not did_occur_recently(dsg.time_last_pounced_at_intruder, 10.0):
                await robot.play_anim_trigger(cozmo.anim.Triggers.CubePouncePounceNormal).wait_for_completed()
                dsg.time_last_pounced_at_intruder = time.time()

            # Turn towards the intruder to keep them in view
            await robot.turn_towards_face(intruder_face).wait_for_completed()
        else:
            # Possibly an intruder - turn backpack blue to indicate, and play
            # suspicious animation (if not played recently)

            robot.set_all_backpack_lights(cozmo.lights.blue_light)
            if not did_occur_recently(dsg.time_last_suspicious, 10.0):
                await robot.play_anim_trigger(cozmo.anim.Triggers.HikingInterestingEdgeThought).wait_for_completed()
                dsg.time_last_suspicious = time.time()
            else:
                # turn robot towards intruder face slightly to get a better look at them
                await robot.turn_towards_face(intruder_face).wait_for_completed()
    else:
        robot.set_backpack_lights_off()


async def desk_security_guard(robot):
    '''The core of the desk_security_guard program'''

    # Turn on image receiving by the camera
    robot.camera.image_stream_enabled = True

    # Connect Twitter, run async in the background
    twitter_api, twitter_auth = twitter_helpers.init_twitter(twitter_keys)
    stream_to_app_comms = TwitterStreamToAppCommunication()
    stream_listener = SecurityGuardStreamListener(twitter_api, stream_to_app_comms)
    twitter_stream = twitter_helpers.CozmoStream(twitter_auth, stream_listener)
    twitter_stream.async_userstream(_with='user')

    # Create our security guard
    dsg = DeskSecurityGuard(twitter_api)

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

        # Handle any external requests to arm or disarm Cozmo
        if stream_to_app_comms.has_arm_request:
            stream_to_app_comms.has_arm_request = False
            if not dsg.is_armed:
                print("Alarm Armed")
                dsg.is_armed = True
        if stream_to_app_comms.has_disarm_request:
            stream_to_app_comms.has_disarm_request = False
            if dsg.is_armed:
                print("Alarm Disarmed")
                dsg.is_armed = False

        stream_to_app_comms.is_armed = dsg.is_armed

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

