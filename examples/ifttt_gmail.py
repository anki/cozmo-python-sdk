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

'''Use IFTTT to make Cozmo inform you when your Gmail account receives an email.

This example shows how you can receive a web request from IFTTT, using a web endpoint
served by Flask. TODO add instructions for how to set it up on IFTTT, etc.
'''

import json
import sys

import flask_helpers
import cozmo


try:
    from flask import Flask, request
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install flask` to install")

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install Pillow` to install")


flask_app = Flask(__name__)
ifttt_gmail = None


class IFTTTGmail:

    def __init__(self, coz):
        self.cozmo = coz


@flask_app.route('/iftttGmail', methods=['POST'])
def handle_iftttGmail():
    '''Called from web request sent by IFTTT when Gmail account receives email'''
    # TODO use the data from the POST (see message below)
    message = json.loads(request.data.decode("utf-8"))
    print(message)

    if ifttt_gmail:

        try:
            # TODO raise head: ifttt_gmail.cozmo.move_head(head_vel)
            # TODO move lift down: ifttt_gmail.cozmo.move_lift(lift_vel)
            ifttt_gmail.cozmo.say_text("New email")
        except cozmo.exceptions.RobotBusy:
            pass

    return ""


def run(sdk_conn):
    robot = sdk_conn.wait_for_robot()

    global ifttt_gmail
    ifttt_gmail = IFTTTGmail(robot)

    # TODO stop opening web page for this example
    flask_helpers.run_flask(flask_app)

if __name__ == '__main__':
    cozmo.setup_basic_logging()
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
