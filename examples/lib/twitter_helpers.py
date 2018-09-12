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

'''Twitter helper functions

Wrapper functions for integrating Cozmo with Twitter using Tweepy.
'''

from io import BytesIO
import json
import sys
import cozmo

try:
    from tweepy_wrapper import tweepy, CozmoStream
except SyntaxError as exc:
    if sys.version_info.major >= 3 and sys.version_info.minor >= 7:
        raise ImportError('Tweepy must be higher than version 3.6.0 when running against python 3.7 or higher.\n'
                          'Do `pip3 install --user --upgrade tweepy` to upgrade.  If that does not work, download the\n'
                          'latest tweepy master from github `https://github.com/tweepy/tweepy`.') from exc
    else:
        from tweepy_wrapper_deprecated import tweepy, CozmoStream


def trim_tweet_text(tweet_text):
    '''Trim a tweet to fit the Twitter max-tweet length'''
    max_tweet_length = 140
    concatenated_suffix = "..."
    if len(tweet_text) > max_tweet_length:
        tweet_text = tweet_text[0:(max_tweet_length - len(concatenated_suffix))] + concatenated_suffix
    return tweet_text


def upload_images(twitter_api, images, image_format='jpeg', quality=90):
    '''Upload Image(s) to twitter using the given settings

    Args:
        twitter_api (:class:`tweepy.API`): the Twitter API instance to use
        images (list of :class:`PIL.Image.Image`): images to upload
        image_format (string): file format to upload as (e.g. 'jpeg', 'png')
        quality (int): quality percentage used for (Jpeg) compression

    Returns:
        list of media_ids
    '''

    media_ids = []
    for image in images:
        img_io = BytesIO()

        image.save(img_io, image_format, quality=quality)
        filename = "temp." + image_format
        img_io.seek(0)

        upload_res = twitter_api.media_upload(filename, file=img_io)
        media_ids.append(upload_res.media_id)

    return media_ids


def post_tweet(twitter_api, tweet_text, reply_id=None, media_ids=None):
    '''post a tweet to the timeline, trims tweet if appropriate

    Args:
        twitter_api (:class:`tweepy.API`): the Twitter API instance to use
        tweet_text (string): the status text to tweet
        reply_id (int): optional, nests the tweet as reply to that tweet (use id_str element from a tweet)
        media_ids (list of media_ids): optional, media to attach to the tweet

    Returns:
        bool: True if posted successfully, False otherwise
    '''
    tweet_text = trim_tweet_text(tweet_text)
    try:
        twitter_api.update_status(tweet_text, reply_id, media_ids=media_ids)
        return True
    except tweepy.error.TweepError as e:
        cozmo.logger.error("post_tweet Error: " + str(e))
        return False


class CozmoTweetStreamListener(tweepy.StreamListener):
    '''Cozmo wrapper around tweepy.StreamListener
       Handles all data received from twitter stream.
    '''

    def __init__(self, coz, twitter_api):
        super().__init__(api=twitter_api)
        self.cozmo = coz
        self.twitter_api = twitter_api

    def trim_tweet_text(self, tweet_text):
        '''Trim a tweet to fit the Twitter max-tweet length'''
        return trim_tweet_text(tweet_text)

    def upload_images(self, images, image_format='jpeg', quality=90):
        '''Upload Image(s) to twitter using the given settings

        Args:
            twitter_api (:class:`tweepy.API`): the Twitter API instance to use
            images (list of :class:`PIL.Image.Image`): images to upload
            image_format (string): file format to upload as (e.g. 'jpeg', 'png')
            quality (int): quality percentage used for (Jpeg) compression

        Returns:
            list of media_ids
        '''
        return upload_images(self.twitter_api, images, image_format=image_format, quality=quality)

    def post_tweet(self, tweet_text, reply_id=None, media_ids=None):
        ''''post a tweet to the timeline, trims tweet if appropriate
            reply_id is optional, nests the tweet as reply to that tweet (use id_str element from a tweet)
        '''
        tweet_text = self.trim_tweet_text(tweet_text)
        return post_tweet(self.twitter_api, tweet_text, reply_id, media_ids=media_ids)

    def on_tweet_from_user(self, json_data, tweet_text, from_user, is_retweet):
        ''''Called from on_data for anything that looks like a tweet
            Return False to stop stream and close connection.'''
        return True

    def on_non_tweet_data(self, json_data):
        ''''Called from on_data for anything that isn't a tweet
            Return False to stop stream and close connection.'''
        return True

    def on_data(self, raw_data):
        '''Called on all data (e.g. any twitter activity/action), including when we receive tweets
           Return False to stop stream and close connection.
        '''

        # parse data string into Json so we can inspect the contents
        json_data = json.loads(raw_data.strip())

        # is this a tweet?
        tweet_text = json_data.get('text')
        from_user = json_data.get('user')
        is_retweet = json_data.get('retweeted')
        is_tweet = (tweet_text is not None) and (from_user is not None) and (is_retweet is not None)

        if is_tweet:
            return self.on_tweet_from_user(json_data, tweet_text, from_user, is_retweet)
        else:
            return self.on_non_tweet_data(json_data)


def has_default_twitter_keys(twitter_keys):
    default_key = 'XXXXXXXXXX'
    return (twitter_keys.CONSUMER_KEY == default_key) and (twitter_keys.CONSUMER_SECRET == default_key) and \
           (twitter_keys.ACCESS_TOKEN == default_key) and (twitter_keys.ACCESS_TOKEN_SECRET == default_key)


def auth_twitter(twitter_keys):
    '''Perform OAuth authentication with twitter, using the keys provided'''
    if has_default_twitter_keys(twitter_keys):
        cozmo.logger.error("You need to configure your twitter_keys")

    auth = tweepy.OAuthHandler(twitter_keys.CONSUMER_KEY, twitter_keys.CONSUMER_SECRET)
    auth.set_access_token(twitter_keys.ACCESS_TOKEN, twitter_keys.ACCESS_TOKEN_SECRET)
    return auth


def delete_all_tweets(twitter_api):
    '''Helper method to delete every tweet we ever made'''
    for status in tweepy.Cursor(twitter_api.user_timeline).items():
        try:
            twitter_api.destroy_status(status.id)
            cozmo.logger.info("Deleted Tweet " + str(status.id) +" = '" + status.text + "'")
        except Exception as e:
            cozmo.logger.info("Exception '" + str(e) + "' trying to Delete Tweet " + str(status.id) + " = '" + status.text + "'")


def init_twitter(twitter_keys):
    auth = auth_twitter(twitter_keys)
    twitter_api = tweepy.API(auth)
    return twitter_api, auth
