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


'''Use "If This Then That" (http://ifttt.com) to make Cozmo inform you when your Gmail account receives an email.

This example shows how you can receive and respond to a web request from If This Then That, using a web endpoint
served by Flask.

To set up the example:
    1) Get a static ip or public URL that you can respond to on your computer. One easy way to do this is with ngrok.
        a) Follow instructions here: https://ngrok.com/download
        b) One ngrok is installed, run this at the command line:
                ./ngrok http 5000
        c) In the ngrok UI in the terminal, note the HTTP forwarding address (e.g., http://55e57164.ngrok.io).
            You will use this address in your recipe.
    2) Set up your recipe on the "If This Then That" website.
        a) Create a Free IFTTT Account:
            https://ifttt.com/join
        b) Select the Maker channel as a channel that interests you
        c) Navigate to: https://ifttt.com/myrecipes/personal
        d) Click “Create a Recipe"
        e) Click "this"
        f) Click "Gmail"
        g) Click “Connect"
        h) Select your Gmail account
        i) Click “Allow” to provide permissions to IFTTT for your email account
        j) Click “Done"
        k) Click “Continue to the next step"
        l) Click “Any new email in inbox"
        m) Click “Create Trigger"
        n) Click “that"
        o) Click “Maker"
        p) Click “Make a web request"
        q) In section “Complete Action Fields”, fill out the fields as follows. Remember your publicly accessble URL, static ip or ngrok dynamic URL (e.g., http://55e57164.ngrok.io):
             URL: http://55e57164.ngrok.io/iftttGmail
             Method: POST
             Content Type: application/json
             Body: {"FromAddress":"{{FromAddress}}"}
        r) Click “Create Action"
        s) Click “Create Recipe"
        t) Click “Check now”. Confirm that IFTTT confirms that the recipe was checked successfully.
        u) Click “Publish”. Add Recipe Title. Publish the recipe.
        v) Click “Add” to add the recipe to your IFTTT account.
        w) Test your recipe by sending an email to your Gmail account:
            1. Run this SDK script: ./ifttt_gmail.py
            2. On your IFTTT receipt webpage, click “Check now”.
'''

import json
import re
import sys
sys.path.append('../')

import cozmo
import flask_helpers
import if_this_then_that_helpers


try:
    from flask import Flask, request
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install flask` to install")


flask_app = Flask(__name__)
ifttt = None


def then_that_action(email_local_part):
    try:
        with ifttt.perform_operation_off_charger(ifttt.cozmo):
            ifttt.cozmo.play_anim(name='ID_pokedB').wait_for_completed()
            ifttt.cozmo.say_text("Email from " + email_local_part).wait_for_completed()

            # TODO replace with email image
            ifttt.display_image_on_face("../images/hello_world.png")

    except cozmo.exceptions.RobotBusy:
        pass


@flask_app.route('/iftttGmail', methods=['POST'])
def receive_ifttt_web_request():
    '''Web request endpoint named "iftttGmail" for IFTTT to call when an email is received.

        In the IFTTT web request, in the URL field, specify this method
        as the endpoint. For instance, if your public url is http://my.url.com,
        then in the IFTTT web request URL field put the following:
        http://my.url.com/iftttGmail. Then, this endpoint will be called when
        IFTTT checks whether the Gmail account received email.
    '''
    json_object = json.loads(request.data.decode("utf-8"))
    from_email_address = json_object["FromAddress"]

    # Use a regular expression to break apart pieces of the email address
    match_object = re.search(r'([\w.]+)@([\w.]+)', from_email_address)

    if ifttt:
        ifttt.queue.put((then_that_action, match_object.group(1)))

    return ""


def run(sdk_conn):
    robot = sdk_conn.wait_for_robot()

    global ifttt
    ifttt = if_this_then_that_helpers.IfThisThenThatHelper(robot)

    flask_helpers.run_flask(flask_app, "127.0.0.1", 5000, False, False)

    # Putting None on the queue stops the thread. This is called when the
    # user hits Control C, which stops the run_flask call.
    ifttt.queue.put(None)


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False  # Cozmo can stay on his charger for this example
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
