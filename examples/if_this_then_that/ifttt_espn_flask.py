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


'''"If This Then That" ESPN example

This example demonstrates how "If This Then That" (http://ifttt.com) can be used
make Cozmo respond when there is an in-game or final score update for the team
you specify. Instructions below will lead you through setting up an applet on
the IFTTT website. When the applet trigger is called (which sends a web request
received by the flask server started in this example), Cozmo will play an animation,
show "ESPN update" on his face, and speak the in-game update.

Please place Cozmo on the charger for this example. When necessary, he will be
rolled off and back on.

Follow these steps to set up and run the example:
    1) Provide a a static ip, URL or similar that can be reached from the "If This
        Then That" server. One easy way to do this is with ngrok, which sets up
        a secure tunnel to localhost running on your machine.

        To set up ngrok:
        a) Follow instructions here to download and install:
            https://ngrok.com/download
        b) Run this command to create a secure public URL for port 8080:
            ./ngrok http 8080
        c) Note the HTTP forwarding address shown in the terminal (e.g., http://55e57164.ngrok.io).
            You will use this address in your applet, below.

        WARNING: Using ngrok exposes your local web server to the internet. See the ngrok
        documentation for more information: https://ngrok.com/docs

    2) Set up your applet on the "If This Then That" website.
        a) Sign up and sign into https://ifttt.com
        b) Create an applet: https://ifttt.com/create
        c) Set up your trigger.
            1. Click "this".
            2. Select "ESPN" as your service.
            3. Under "Choose a Trigger", select “New in-game update".
            4. In section "Complete Trigger Fields", enter your sport and team and click “Create Trigger".

        d) Set up your action.
            1. Click “that".
            2. Select “Maker" to set it as your action channel. Connect to the Maker channel if prompted.
            3. Click “Make a web request" and fill out the fields as follows. Remember your publicly
                accessible URL from above (e.g., http://55e57164.ngrok.io) and use it in the URL field,
                followed by "/iftttESPN" as shown below:

                 URL: http://55e57164.ngrok.io/iftttESPN
                 Method: POST
                 Content Type: application/json
                 Body: {"AlertBody":"{{AlertBody}}"}

            5. Click “Create Action" then “Finish".

    3) Test your applet.
        a) Run this script at the command line: ./ifttt_espn.py
        b) On ifttt.com, on your applet page, click “Check now”. See that IFTTT confirms that the applet
            was checked.
        c) Wait for new in-game updates for your team and see Cozmo react! Cozmo should roll off the charger, raise
            and lower his lift, show "ESPN update" on his face and speak the in-game update.
'''

from contextlib import contextmanager

import json
import queue
import sys
sys.path.append('../')
import threading
import time

import cozmo
import flask_helpers

from common import IFTTTRobot


try:
    from flask import Flask, request
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install flask` to install")


flask_app = Flask(__name__)
ifttt_queue = queue.Queue()
robot = None


def then_that_action(alert_body):
    '''Controls how Cozmo responds to the in-game update.

    You may modify this method to change how Cozmo reacts to
    the update from ESPN.
    '''

    try:
        with perform_operation_off_charger(robot):
            '''If necessary, Move Cozmo's Head and Lift to make it easy to see Cozmo's face.'''
            robot.get_in_position()

            # First, have Cozmo play animation "ID_pokedB", which tells
            # Cozmo to raise and lower his lift. To change the animation,
            # you may replace "ID_pokedB" with another animation. Run
            # remote_control_cozmo.py to see a list of animations.
            robot.play_anim(name='ID_pokedB').wait_for_completed()

            # Next, have Cozmo speak the text from the in-game update.
            robot.say_text(alert_body).wait_for_completed()

            # Last, have Cozmo display a sports image on his face.
            robot.display_image_file_on_face("../images/ifttt_espn.png")


    except cozmo.exceptions.RobotBusy:
        pass


def backup_onto_charger(robot):
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
def perform_operation_off_charger(robot):
    '''Perform a block of code with robot off the charger

    Ensure robot is off charger before yielding
    yield - (at which point any code in the caller's with block will run).
    If Cozmo started on the charger then return it back afterwards'''

    was_on_charger = robot.is_on_charger
    robot.drive_off_charger_contacts().wait_for_completed()

    yield robot

    if was_on_charger:
        backup_onto_charger(robot)


@flask_app.route('/iftttESPN', methods=['POST'])
def receive_ifttt_web_request():
    '''Web request endpoint named "iftttESPN" for IFTTT to call when a new in-game
        update for your team is posted on ESPN.

        In the IFTTT web request, in the URL field, specify this method
        as the endpoint. For instance, if your public url is http://my.url.com,
        then in the IFTTT web request URL field put the following:
        http://my.url.com/iftttESPN. Then, this endpoint will be called when
        IFTTT checks and discovers that a new in-game update for your team is
        posted on ESPN.
    '''

    # Retrieve the data passed by If This Then That in the web request body.
    json_object = json.loads(request.data.decode("utf-8"))

    # Extract the text for the in-game update.
    alert_body = json_object["AlertBody"]

    # Add this email to the queue of emails awaiting Cozmo's reaction.
    ifttt_queue.put((then_that_action, alert_body))

    # Return promptly so If This Then That knows that the web request was received
    # successfully.
    return ""


def worker():
    while True:
        item = ifttt_queue.get()
        if item is None:
            break
        queued_action, action_args = item
        queued_action(action_args)


def run(sdk_conn):
    global robot
    robot = sdk_conn.wait_for_robot()

    threading.Thread(target=worker).start()

    # Start flask web server so that /iftttESPN can serve as endpoint.
    flask_helpers.run_flask(flask_app, "127.0.0.1", 8080, False, False)

    # Putting None on the queue stops the thread. This is called when the
    # user hits Control C, which stops the run_flask call.
    ifttt_queue.put(None)


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False  # Cozmo can stay on his charger for this example

    # Use our custom robot class with extra helper methods
    cozmo.conn.CozmoConnection.robot_factory = IFTTTRobot

    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)

