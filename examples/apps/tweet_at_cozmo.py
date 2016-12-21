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

'''Control Cozmo with tweets

Example for integrating Cozmo with Twitter
Lets you tweet at your Cozmo to control the robot
See cozmo_twitter_keys.py for details on how to setup a Twitter account for your Cozmo and get access keys
'''

import sys

import cozmo
from cozmo.util import degrees
sys.path.append('../lib/')
import twitter_helpers
import cozmo_twitter_keys as twitter_keys


def extract_float(cmd_args, index=0):
    if len(cmd_args) > index:
        try:
            float_val = float(cmd_args[index])
            return float_val
        except ValueError:
            pass
    return None


class ReactToTweetsStreamListener(twitter_helpers.CozmoTweetStreamListener):
    '''React to Tweets sent to our Cozmo, live, as they happen...'''

    def __init__(self, coz, twitter_api):
        super().__init__(coz, twitter_api)


    # Useful during development - an easy way to delete all of Cozmo's tweets
    # def do_deleteall(self, cmd_args, kw_args):
    #     cozmo.logger.info('Deleting all of your tweets')
    #     twitter_helpers.delete_all_tweets(self.twitter_api)
    #     return None


    def do_drive(self, cmd_args, kw_args):
        """drive X"""
        usage = "'drive X' where X is number of seconds to drive for"
        error_message = ""

        drive_duration = extract_float(cmd_args)

        if drive_duration is not None:
            drive_speed = 50
            drive_dir = "forwards"
            if drive_duration < 0:
                drive_speed = -drive_speed
                drive_duration = -drive_duration
                drive_dir = "backwards"

            self.cozmo.drive_wheels(drive_speed, drive_speed, duration=drive_duration)
            return "I drove " + drive_dir + " for " + str(drive_duration) + " seconds!"

        return "Error: usage = " + usage + error_message


    def do_turn(self, cmd_args, kw_args):
        usage = "'turn X' where X is a number of degrees to turn"

        drive_angle = extract_float(cmd_args)

        if drive_angle is not None:
            self.cozmo.turn_in_place(degrees(drive_angle)).wait_for_completed()
            return "I turned " + str(drive_angle) + " degrees!"

        return "Error: usage = " + usage


    def do_lift(self, cmd_args, kw_args):
        usage = "'lift X' where X is desired height for lift"

        lift_height = extract_float(cmd_args)

        if lift_height is not None:
            self.cozmo.set_lift_height(height=lift_height).wait_for_completed()
            return "I moved lift to " + str(lift_height)

        return "Error: usage = " + usage


    def do_head(self, cmd_args, kw_args):
        usage = "'head X' where X is desired angle for head" #-25 (down) to 44.5 degrees (up)

        head_angle = extract_float(cmd_args)

        if head_angle is not None:
            head_angle_action = self.cozmo.set_head_angle(degrees(head_angle))
            clamped_head_angle = head_angle_action.angle.degrees
            head_angle_action.wait_for_completed()
            resultString = "I moved head to " + "{0:.1f}".format(clamped_head_angle)
            if abs(head_angle - clamped_head_angle) > 0.01:
                resultString += " (clamped to range)"
            return resultString

        return "Error: usage = " + usage


    def do_say(self, cmd_args, kw_args):
        usage = "'say X' where X is any text for cozmo to say"

        entire_message = None
        if len(cmd_args) > 0:
            try:
                entire_message = ""
                for s in cmd_args:
                    entire_message = entire_message + " " + str(s)
                entire_message = entire_message.strip()
            except:
                pass

        if (entire_message is not None) and (len(entire_message) > 0):
            self.cozmo.say_text(entire_message).wait_for_completed()
            return 'I said "' + entire_message + '"!'

        return "Error: usage = " + usage


    def do_photo(self, cmd_args, kw_args):
        '''Upload a photo of what Cozmo can currently see (no cmd_args used)'''
        latest_image = self.cozmo.world.latest_image
        if latest_image is not None:
            status_text = kw_args["reply_prefix"] + "here's your photo:"
            reply_id = kw_args.get("tweet_id", None)
            media_ids = self.upload_images([latest_image.raw_image])
            posted_image = self.post_tweet(status_text, reply_id=reply_id, media_ids=media_ids)
            if posted_image:
                return None # indicate that we don't need to tweet an additional reply
            else:
                return "Error: Failed to tweet image"
        else:
            return "Error: I have no photos"


    def get_supported_commands(self):
        '''Construct a list of all methods in this class that start with "do_" - these are commands we accept'''
        prefix_str = "do_"
        prefix_len = len(prefix_str)
        supported_commands = []
        for func_name in dir(self.__class__):
            if func_name.startswith(prefix_str):
                supported_commands.append(func_name[prefix_len:])
        return supported_commands


    def get_command(self, command_name):
        '''Find a matching "do_" function and return it. return None if there's no match'''
        try:
            return getattr(self, 'do_' + command_name.lower())
        except AttributeError:
            return None


    def extract_command_from_string(self, in_string):
        '''Separate inString at each space, loop through until we find a command, return tuple of cmd_func and cmd_args'''

        split_string = in_string.split()

        for i in range(len(split_string)):

            cmd_func = self.get_command(split_string[i])

            if cmd_func:
                cmd_args = split_string[i + 1:]
                return cmd_func, cmd_args

        # No valid command found
        return None, None


    def on_tweet_from_user(self, json_data, tweet_text, from_user, is_retweet):
        '''Handle every new tweet as it appears'''

        # ignore retweets
        if is_retweet:
            return True

        # ignore any replies from this account (otherwise we'd infinite loop as soon as we reply)
        # allow other messages from this account (so you can tweet at yourself to control Cozmo if you want)

        user_me = self.twitter_api.me()
        is_from_me = (from_user.get('id') == user_me.id)

        if is_from_me and tweet_text.startswith("@"):
            # ignore replies from this account
            return

        from_user_name = from_user.get('screen_name')

        tweet_id = json_data.get('id_str')

        cmd_func, cmd_args = self.extract_command_from_string(tweet_text)

        reply_prefix = "@" + from_user_name + " "
        if cmd_func is not None:
            kw_args = {'tweet_id': tweet_id, 'reply_prefix': reply_prefix}
            result_string = cmd_func(cmd_args, kw_args)
            if result_string:
                self.post_tweet(reply_prefix + result_string, tweet_id)
        else:
            self.post_tweet(reply_prefix + "Sorry I don't understand, available commands are: "
                            + str(self.get_supported_commands()), tweet_id)


def run(coz_conn):
    '''The run method runs once Cozmo is connected.'''
    coz = coz_conn.wait_for_robot()

    # Turn on image receiving by the camera
    coz.camera.image_stream_enabled = True

    twitter_api, twitter_auth = twitter_helpers.init_twitter(twitter_keys)
    stream_listener = ReactToTweetsStreamListener(coz, twitter_api)
    twitter_stream = twitter_helpers.CozmoStream(twitter_auth, stream_listener)
    twitter_stream.userstream(_with='user')


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
