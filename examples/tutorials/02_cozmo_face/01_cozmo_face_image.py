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

'''Display images on Cozmo's face (oled screen)
'''

import os
import sys
import time

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

import cozmo


def get_in_position(robot: cozmo.robot.Robot):
    '''If necessary, Move Cozmo's Head and Lift to make it easy to see Cozmo's face'''
    if (robot.lift_height.distance_mm > 45) or (robot.head_angle.degrees < 40):
        with robot.perform_off_charger():
            lift_action = robot.set_lift_height(0.0, in_parallel=True)
            head_action = robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE,
                                               in_parallel=True)
            lift_action.wait_for_completed()
            head_action.wait_for_completed()


def cozmo_program(robot: cozmo.robot.Robot):
    current_directory = os.path.dirname(os.path.realpath(__file__))
    get_in_position(robot)
    sdk_png = os.path.join(current_directory, "..", "..", "face_images", "cozmosdk.png")
    hello_png = os.path.join(current_directory, "..", "..", "face_images", "hello_world.png")

    # load some images and convert them for display cozmo's face
    image_settings = [(sdk_png, Image.BICUBIC),
                      (hello_png, Image.NEAREST)]
    face_images = []
    for image_name, resampling_mode in image_settings:
        image = Image.open(image_name)

        # resize to fit on Cozmo's face screen
        resized_image = image.resize(cozmo.oled_face.dimensions(), resampling_mode)

        # convert the image to the format used by the oled screen
        face_image = cozmo.oled_face.convert_image_to_screen_data(resized_image,
                                                                 invert_image=True)
        face_images.append(face_image)

    # display each image on Cozmo's face for duration_s seconds (Note: this
    # is clamped at 30 seconds max within the engine to prevent burn-in)
    # repeat this num_loops times

    num_loops = 10
    duration_s = 2.0

    print("Press CTRL-C to quit (or wait %s seconds to complete)" % int(num_loops*duration_s) )

    for _ in range(num_loops):
        for image in face_images:
            robot.display_oled_face_image(image, duration_s * 1000.0)
            time.sleep(duration_s)


# Cozmo is moved off his charger contacts by default at the start of any program.
# This is because not all motor movement is possible whilst drawing current from
# the charger. In cases where motor movement is not required, such as this example
# we can specify that Cozmo can stay on his charger at the start:
cozmo.robot.Robot.drive_off_charger_on_connect = False

cozmo.run_program(cozmo_program)

