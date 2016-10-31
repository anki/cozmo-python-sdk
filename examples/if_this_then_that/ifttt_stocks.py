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


'''"If This Then That" Stock example

This example demonstrates how "If This Then That" (http://ifttt.com) can be used
make Cozmo respond when a stock ticker symbol increases by 1% or more. Instructions
below will lead you through setting up a "recipe" on the IFTTT website. When the recipe
trigger is called (which sends a web request received by the flask server started
in this example), Cozmo will play an animation, speak the company name and the
percentage increase, and show a stock market image on his face.

Please place Cozmo on the charger for this example. When necessary, he will be
rolled off and back on.

Follow these steps to run the example:
    1) Provide a a static ip, URL or similar that can be reached from the If This
        Then That server. One easy way to do this is with ngrok, which sets up
        a secure tunnel to localhost running on your machine.

        To set up ngrok:

        a) Follow instructions here to download and install:
            https://ngrok.com/download
        b) Run this command to create a secure public URL for port 5000:
            ./ngrok http 5000
        c) Note the HTTP forwarding address shown in the terminal (e.g., http://55e57164.ngrok.io).
            You will use this address in your recipe, below.

    2) Set up your recipe on the "If This Then That" website.
        a) Sign up and sign into https://ifttt.com
        b) Create a recipe: https://ifttt.com/myrecipes/personal/new
        c) Set up your trigger.
            1. Click "this".
            2. Select "Stocks" as  your trigger channel.
            3. Under "Choose a Trigger", select “Today's price rises by percentage".
            4. In section "Complete Trigger Fields", enter your ticker symbol and desired percentage,
                for instance:

                Ticker symbol: HOG
                Percentage increase: 1

            5. Click “Create Trigger".

        d) Set up your action.
            1. Click “that".
            2. Click “Maker" to set it as your action channel. Connect to the Maker channel if prompted.
            3. Click “Make a web request".
            4. In section “Complete Action Fields”, fill out the fields as follows. Remember your publicly
                accessible URL from above (e.g., http://55e57164.ngrok.io) and use it in the URL field,
                followed by "/iftttStocks" as shown below:

                 URL: http://55e57164.ngrok.io/iftttStocks
                 Method: POST
                 Content Type: application/json
                 Body: {"PercentageChange":"{{PercentageChange}}","StockName":"{{StockName}}"}

            5. Click “Create Action" then “Create Recipe".

    3) Test your recipe
        a) Run this script at the command line: ./ifttt_stocks.py
        b) On ifttt.com, on your recipe page, click “Check now”. See that IFTTT confirms that the recipe
            was checked successfully.
        c) Wait for your stock to increase and see Cozmo react! Cozmo should roll off the charger, raise
            and lower his lift, announce the stock increase, and then show a stock market image on his face.
'''

import json
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


def then_that_action(parameters):
    stock_name, percentage = parameters

    try:
        with ifttt.perform_operation_off_charger():
            ifttt.cozmo.play_anim(name='ID_pokedB').wait_for_completed()
            ifttt.cozmo.say_text(stock_name + " is up " + percentage + " percent").wait_for_completed()

            # TODO replace with stock image
            ifttt.display_image_file_on_face("../images/hello_world.png")

    except cozmo.exceptions.RobotBusy:
        pass


@flask_app.route('/iftttStocks', methods=['POST'])
def receive_ifttt_web_request():
    '''Web request endpoint named "iftttStocks" for IFTTT to call when the
        selected ticker symbol increases by 1% or more.

        In the IFTTT web request, in the URL field, specify this method
        as the endpoint. For instance, if your public url is http://my.url.com,
        then in the IFTTT web request URL field put the following:
        http://my.url.com/iftttStocks. Then, this endpoint will be called when
        IFTTT checks and discovers that the selected ticker symbol has increased
        by 1% or more.
    '''
    json_object = json.loads(request.data.decode("utf-8"))
    stock_name = json_object["StockName"]
    percentage_change = str(json_object["PercentageChange"])

    if ifttt:
        ifttt.queue.put((then_that_action, (stock_name, percentage_change)))

    return ""


def run(sdk_conn):
    robot = sdk_conn.wait_for_robot()

    global ifttt
    ifttt = if_this_then_that_helpers.IfThisThenThatHelper(robot)

    # Start flask web server so that /iftttStocks can serve as endpoint.
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
