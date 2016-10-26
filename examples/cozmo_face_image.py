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

import sys
import time

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

import cozmo


def run(sdk_conn):
    '''The run method runs once Cozmo is connected.'''

    robot = sdk_conn.wait_for_robot()

    # move head and lift to make it easy to see Cozmo's face
    robot.set_lift_height(0.0).wait_for_completed()
    robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

    # load some images and convert them for display cozmo's face
    image_settings = [("images/cozmosdk.png", Image.BICUBIC),
                      ("images/hello_world.png", Image.NEAREST)]
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

    for _ in range(num_loops):
        for image in face_images:
            robot.display_oled_face_image(image, duration_s * 1000.0)
            time.sleep(duration_s)


if __name__ == '__main__':
    cozmo.setup_basic_logging()
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
