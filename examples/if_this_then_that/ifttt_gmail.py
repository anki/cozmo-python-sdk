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


'''"If This Then That" Gmail example

This example demonstrates how "If This Then That" (http://ifttt.com) can be used
make Cozmo respond when a Gmail account receives an email. Instructions below
will lead you through setting up an applet on the IFTTT website. When the applet
trigger is called (which sends a web request received by the web server started
in this example), Cozmo will play an animation, speak the email sender's name and
show a mailbox image on his face.

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
            2. Select "Gmail" as your service. If prompted, click "Connect",
                select your Gmail account, and click “Allow” to provide permissions
                to IFTTT for your email account. Click "Done".
            3. Under "Choose a Trigger", select “Any new email in inbox".
        d) Set up your action.
            1. Click “that".
            2. Select “Maker Webhooks" to set it as your action channel. Connect to the Maker channel if prompted.
            3. Click “Make a web request" and fill out the fields as follows. Remember your publicly
                accessible URL from above (e.g., http://55e57164.ngrok.io) and use it in the URL field,
                followed by "/iftttGmail" as shown below:

                 URL: http://55e57164.ngrok.io/iftttGmail
                 Method: POST
                 Content Type: application/json
                 Body: {"FromAddress":"{{FromAddress}}"}

            5. Click “Create Action" then “Finish".

    3) Test your applet.
        a) Run this script at the command line: ./ifttt_gmail.py
        b) On ifttt.com, on your applet page, click “Check now”. See that IFTTT confirms that the applet
            was checked.
        c) Send an email to the Gmail account in your recipe
        d) On your IFTTT applet webpage, again click “Check now”. This should cause IFTTT to detect that
            the email was received and send a web request to the ifttt_gmail.py script.
        e) In response to the ifttt web request, Cozmo should roll off the charger, raise and lower
            his lift, announce the email, and then show a mailbox image on his face.
'''

import asyncio
import re
import sys


try:
    from aiohttp import web
except ImportError:
    sys.exit("Cannot import from aiohttp. Do `pip3 install --user aiohttp` to install")

import cozmo

from common import IFTTTRobot


app = web.Application()


async def serve_gmail(request):
    '''Define an HTTP POST handler for receiving requests from If This Then That.

    You may modify this method to change how Cozmo reacts to the email
    being received.
    '''

    json_object = await request.json()

    # Extract the name of the email sender.
    from_email_address = json_object["FromAddress"]

    # Use a regular expression to break apart pieces of the email address
    match_object = re.search(r'([\w.]+)@([\w.]+)', from_email_address)
    email_local_part = match_object.group(1)

    robot = request.app['robot']
    async def read_name():
        try:
            async with robot.perform_off_charger():
                '''If necessary, Move Cozmo's Head and Lift to make it easy to see Cozmo's face.'''
                await robot.get_in_position()

                # First, have Cozmo play an animation
                await robot.play_anim_trigger(cozmo.anim.Triggers.ReactToPokeStartled).wait_for_completed()

                # Next, have Cozmo speak the name of the email sender.
                await robot.say_text("Email from " + email_local_part).wait_for_completed()

                # Last, have Cozmo display an email image on his face.
                robot.display_image_file_on_face("../face_images/ifttt_gmail.png")

        except cozmo.RobotBusy:
            cozmo.logger.warning("Robot was busy so didn't read email address: "+ from_email_address)

    # Perform Cozmo's task in the background so the HTTP server responds immediately.
    asyncio.ensure_future(read_name())

    return web.Response(text="OK")

# Attach the function as an HTTP handler.
app.router.add_post('/iftttGmail', serve_gmail)


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False

    # Use our custom robot class with extra helper methods
    cozmo.conn.CozmoConnection.robot_factory = IFTTTRobot

    try:
        app_loop = asyncio.get_event_loop()  
        sdk_conn = cozmo.connect_on_loop(app_loop)

        # Wait for the robot to become available and add it to the app object.
        app['robot'] = app_loop.run_until_complete(sdk_conn.wait_for_robot())
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)

    web.run_app(app)
