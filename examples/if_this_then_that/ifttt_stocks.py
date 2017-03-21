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
below will lead you through setting up an applet on the IFTTT website. When the applet
trigger is called (which sends a web request received by the web server started
in this example), Cozmo will play an animation, speak the company name and the
percentage increase, and show a stock market image on his face.

Please place Cozmo on the charger for this example. When necessary, he will be
rolled off and back on.

Follow these steps to set up and run the example:
    1) Provide a a static ip, URL or similar that can be reached from the If This
        Then That server. One easy way to do this is with ngrok, which sets up
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
            2. Select "Stocks" as your service.
            3. Under "Choose a Trigger", select “Today's price rises by percentage".
            4. In section "Complete Trigger Fields", enter your ticker symbol and desired percentage,
                for instance:

                Ticker symbol: HOG
                Percentage increase: 1

            5. Click “Create Trigger".

        d) Set up your action.
            1. Click “that".
            2. Select “Maker" to set it as your action channel. Connect to the Maker channel if prompted.
            3. Click “Make a web request" and fill out the fields as follows. Remember your publicly
                accessible URL from above (e.g., http://55e57164.ngrok.io) and use it in the URL field,
                followed by "/iftttStocks" as shown below:

                 URL: http://55e57164.ngrok.io/iftttStocks
                 Method: POST
                 Content Type: application/json
                 Body: {"PercentageChange":"{{PercentageChange}}","StockName":"{{StockName}}"}

            5. Click “Create Action" then “Finish".

    3) Test your applet.
        a) Run this script at the command line: ./ifttt_stocks.py
        b) On ifttt.com, on your applet page, click “Check now”. See that IFTTT confirms that the applet
            was checked.
        c) Wait for your stock to increase and see Cozmo react! Cozmo should roll off the charger, raise
            and lower his lift, announce the stock increase, and then show a stock market image on his face.
'''

import asyncio
import sys


try:
    from aiohttp import web
except ImportError:
    sys.exit("Cannot import from aiohttp. Do `pip3 install --user aiohttp` to install")

import cozmo

from common import IFTTTRobot


app = web.Application()


async def serve_stocks(request):
    '''Define an HTTP POST handler for receiving requests from If This Then That.

    Controls how Cozmo responds to stock notification. You may modify this method
    to change how Cozmo reacts to the stock price increasing.
    '''

    json_object = await request.json()

    # Extract the company name for the stock ticker symbol.
    stock_name = json_object["StockName"]

    # Extract the percentage increase.
    percentage = str(json_object["PercentageChange"])

    robot = request.app['robot']
    async def read_name():
        try:
            async with robot.perform_off_charger():
                '''If necessary, Move Cozmo's Head and Lift to make it easy to see Cozmo's face.'''
                await robot.get_in_position()

                # First, have Cozmo play animation "ID_pokedB", which tells
                # Cozmo to raise and lower his lift. To change the animation,
                # you may replace "ID_pokedB" with another animation. Run
                # remote_control_cozmo.py to see a list of animations.
                await robot.play_anim(name='ID_pokedB').wait_for_completed()

                # Next, have Cozmo say that your stock is up by x percent.
                await robot.say_text(stock_name + " is up " + percentage + " percent").wait_for_completed()

                # Last, have Cozmo display a stock market image on his face.
                robot.display_image_file_on_face("../face_images/ifttt_stocks.png")

        except cozmo.RobotBusy:
            cozmo.logger.warning("Robot was busy so didn't read stock update: '"+ stock_name + " is up " + percentage + " percent'.")

    # Perform Cozmo's task in the background so the HTTP server responds immediately.
    asyncio.ensure_future(read_name())

    return web.Response(text="OK")

# Attach the function as an HTTP handler.
app.router.add_post('/iftttStocks', serve_stocks)


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False

    # Use our custom robot class with extra helper methods
    cozmo.conn.CozmoConnection.robot_factory = IFTTTRobot

    try:
        sdk_conn = cozmo.connect_on_loop(app.loop)
        # Wait for the robot to become available and add it to the app object.
        app['robot'] = app.loop.run_until_complete(sdk_conn.wait_for_robot())
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)

    web.run_app(app)
