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

from contextlib import contextmanager
import json
import queue
import re
import sys
import threading
import time

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


def then_that_action(email_local_part):
    try:
        with ifttt_gmail.perform_operation_off_charger(ifttt_gmail.cozmo):
            ifttt_gmail.cozmo.play_anim(name='ID_pokedB').wait_for_completed()
            ifttt_gmail.cozmo.say_text("Email from " + email_local_part).wait_for_completed()

            # TODO replace with email image
            ifttt_gmail.display_image_on_face("images/hello_world.png")

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

    if ifttt_gmail:
        ifttt_gmail.queue.put((then_that_action, match_object.group(1)))

    return ""


class IFTTTGmail:

    def __init__(self, coz):
        self.cozmo = coz
        self.queue = queue.Queue()

        '''Start a separate thread to check if the queue contains an action to run.'''
        threading.Thread(target=self.worker).start()

        self.get_in_position(self.cozmo)


    def worker(self):
        while True:
            item = self.queue.get()
            if item is None:
                break
            queued_action, action_args = item
            queued_action(action_args)


    def backup_onto_charger(self, robot):
        '''Attempts to reverse robot onto its charger

        Assumes charger is directly behind Cozmo
        Keep driving straight back until charger is in contact
        '''

        robot.drive_wheels(-30, -30)
        time_waited = 0.0
        while time_waited < 3.0 and not robot.is_on_charger:
            sleep_time_s = 0.1
            time.sleep(sleep_time_s)
            time_waited += sleep_time_s

        robot.stop_all_motors()


    @contextmanager
    def perform_operation_off_charger(self, robot):
        '''Perform a block of code with robot off the charger

        Ensure robot is off charger before yielding
        yield - (at which point any code in the caller's with block will run).
        If Cozmo started on the charger then return it back afterwards'''
        was_on_charger = robot.is_on_charger
        robot.drive_off_charger_contacts().wait_for_completed()

        yield robot

        if was_on_charger:
            self.backup_onto_charger(robot)


    def get_in_position(self, robot):
        '''If necessary, Move Cozmo'qs Head and Lift to make it easy to see Cozmo's face'''
        if (robot.lift_height.distance_mm > 45) or (robot.head_angle.degrees < 40):
            with self.perform_operation_off_charger(robot):
                robot.set_lift_height(0.0).wait_for_completed()
                robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()


    def display_image_on_face(self, image_name):
        # load image and convert it for display on cozmo's face
        image = Image.open(image_name)

        # resize to fit on Cozmo's face screen
        resized_image = image.resize(cozmo.oled_face.dimensions(), Image.NEAREST)

        # convert the image to the format used by the oled screen
        face_image = cozmo.oled_face.convert_image_to_screen_data(resized_image,
                                                                  invert_image=True)

        # display each image on the robot's face for duration_s seconds (Note: this
        # is clamped at 30 seconds max within the engine to prevent burn-in)
        # repeat this num_loops times
        num_loops = 5
        duration_s = 2.0

        for _ in range(num_loops):
            self.cozmo.display_oled_face_image(face_image, duration_s * 1000.0)
            time.sleep(duration_s)


def run(sdk_conn):
    robot = sdk_conn.wait_for_robot()

    global ifttt_gmail
    ifttt_gmail = IFTTTGmail(robot)

    flask_helpers.run_flask(flask_app, "127.0.0.1", 5000, False, False)

    # Put None on the queue to stop the thread. This is called when the
    # user hits Control C, stopping the run_flask call.
    ifttt_gmail.queue.put(None)


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False  # Cozmo can stay on his charger for this example
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
