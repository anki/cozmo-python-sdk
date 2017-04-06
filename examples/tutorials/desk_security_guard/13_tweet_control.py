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

"""Desk Security Guard Tutorial - Example 13 - Tweet Control."""

import asyncio
from random import randint
import sys

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps

sys.path.append('../../lib/')
import twitter_helpers
import cozmo_twitter_keys as twitter_keys


class TwitterStreamToAppCommunication:
    def __init__(self):
        self.request_stop = False


class DeskGuardStreamListener(twitter_helpers.CozmoTweetStreamListener):
    def __init__(self, twitter_api, owner_twitter_handle, stream_to_app_comms):
        super().__init__(None, twitter_api)
        self.owner_twitter_handle = owner_twitter_handle
        self.stream_to_app_comms = stream_to_app_comms

    def on_tweet_from_user(self, json_data, tweet_text, from_user, is_retweet):
        # This will be called on each incoming tweet
        user_name = from_user.get('screen_name')
        if user_name == self.owner_twitter_handle:
            tweet_text = tweet_text.lower()
            if tweet_text.startswith("quit"):
                self.stream_to_app_comms.request_stop = True
            else:
                print("Unknown command '%s'" % tweet_text)
        else:
            print("Ignoring tweet from '%s' (not '%s')" % (user_name, self.owner_twitter_handle))


class DeskGuard:
    def __init__(self, robot: cozmo.robot.Robot, owner_name: str,
                 owner_twitter_handle: str):
        # Turn on image receiving by the camera
        robot.camera.image_stream_enabled = True
        self.robot = robot
        self.owner_name = owner_name
        self.owner_twitter_handle = owner_twitter_handle
        robot.add_event_handler(cozmo.faces.EvtFaceAppeared, self.face_appeared)
        robot.add_event_handler(cozmo.faces.EvtFaceDisappeared, self.face_disappeared)
        self.stream_to_app_comms = TwitterStreamToAppCommunication()
        self.twitter_api = None
        self.connect_twitter()

    def connect_twitter(self):
        # Connect Twitter
        self.twitter_api, twitter_auth = twitter_helpers.init_twitter(twitter_keys)
        # Create a listener for handling tweets as they appear in the stream
        stream_listener = DeskGuardStreamListener(self.twitter_api, self.owner_twitter_handle,
                                                  self.stream_to_app_comms)
        twitter_stream = twitter_helpers.CozmoStream(twitter_auth, stream_listener)
        # run twitter_stream async in the background
        # Note: Tweepy does not use asyncio, so beware of threading issues
        twitter_stream.async_userstream(_with='user')

    def tweet_photo(self, status_text):
        # Get the latest image from Cozmo's camera
        latest_image = self.robot.world.latest_image
        if latest_image is not None:
            # Post a tweet with image and status_text
            media_ids = twitter_helpers.upload_images(self.twitter_api,
                                                      [latest_image.raw_image])
            posted_image = twitter_helpers.post_tweet(self.twitter_api,
                                                      status_text,
                                                      media_ids=media_ids)
        else:
            print("Error: No images have been received from Cozmo")

    def face_appeared(self, evt, face: cozmo.faces.Face, **kwargs):
        if face.name == self.owner_name:
            self.robot.play_anim_trigger(cozmo.anim.Triggers.NamedFaceInitialGreeting,
                                         in_parallel=True)
        else:
            self.robot.say_text("Intruder Alert!", in_parallel = True)
            self.tweet_photo("@" + self.owner_twitter_handle + " Intruder Detected")

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

        while not self.stream_to_app_comms.request_stop:
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
    desk_guard = DeskGuard(robot, "Wez", "MarksCozmo")
    await desk_guard.run()


# Leave Cozmo on his charger at connection, so we can handle it ourselves
cozmo.robot.Robot.drive_off_charger_on_connect = False
cozmo.run_program(cozmo_program)
