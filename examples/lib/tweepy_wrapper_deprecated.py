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

'''Tweepy stream helper class

Cozmo wrapper around tweepy.Stream Primarily just to avoid needing to import tweepy outside
of this file.

Previous to python 3.7, tweepy had a parameter named 'async' which causes
an error if imported in later versions.  To continue supporting earlier versions of python
and tweepy, this deprecated version of the stream helper class is provided.
'''


try:
    import tweepy
except ImportError:
    sys.exit("Cannot import tweepy: Do `pip3 install --user tweepy` to install")

class CozmoStream(tweepy.Stream):

    def async_userstream(self, stall_warnings=False, _with=None, replies=None,
                          track=None, locations=None, run_in_new_thread=True, encoding='utf8'):
        '''Wrapper around :meth:`userstream` for exposing async parameter

        The async variable name in userstream clashes with the async keyword in asyncio
        This wrapper hides the variable name so that it can be called from asyncio code
        '''

        self.userstream(stall_warnings=stall_warnings, _with=_with, replies=replies,\
                        track=track, locations=locations, async=run_in_new_thread,\
                        encoding=encoding)
