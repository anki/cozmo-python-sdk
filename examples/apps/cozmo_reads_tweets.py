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

'''Cozmo reads tweets.

This is an example for integrating Cozmo with Twitter.
Cozmo will read aloud each new tweet as it appears on your Twitter stream.
See user_twitter_keys.py for details on how to setup a Twitter account and get access keys.
'''

import sys

import cozmo
sys.path.append('../lib/')
import twitter_helpers
import user_twitter_keys as twitter_keys


class CozmoReadsTweetsStreamListener(twitter_helpers.CozmoTweetStreamListener):
    '''React to Tweets sent to our Cozmo, live, as they happen...'''

    def __init__(self, coz, twitter_api):
        super().__init__(coz, twitter_api)

    def on_tweet_from_user(self, json_data, tweet_text, from_user, is_retweet):
        '''Called on every tweet that appears in the stream'''

        user_name = from_user.get('screen_name')
        if is_retweet:
            # Remove the redundant RT string at the start of retweets
            rt_prefix = "RT "
            rt_loc = tweet_text.find(rt_prefix)
            if rt_loc >= 0:
                tweet_text = tweet_text[rt_loc+len(rt_prefix):]
            text_to_say = user_name + " retweeted " + tweet_text
        else:
            text_to_say = user_name + " tweeted " + tweet_text

        text_to_say = text_to_say.strip()

        cozmo.logger.info('Cozmo says: "' + text_to_say + '"')

        self.cozmo.say_text(text_to_say).wait_for_completed()


def run(coz_conn):
    '''The run method runs once Cozmo is connected.'''
    coz = coz_conn.wait_for_robot()

    twitter_api, twitter_auth = twitter_helpers.init_twitter(twitter_keys)
    stream_listener = CozmoReadsTweetsStreamListener(coz, twitter_api)
    twitter_stream = twitter_helpers.CozmoStream(twitter_auth, stream_listener)
    twitter_stream.userstream()


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
