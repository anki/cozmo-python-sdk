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

'''If This Then That helper common code.

This module include a subclass of Robot to add some helper methods that are
useful to the IFTTT examples.

This class includes the following:
    1) get_in_position moves Cozmo's lift down and face up if necessary.
    2) display_image_on_face displays the requested image file on his face after
        the If This Then That trigger has been received.
'''

import sys

import cozmo


try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


class IFTTTRobot(cozmo.robot.Robot):
    '''Add some methods to the base Robot class.'''
    async def get_in_position(self):
        '''If necessary, Move Cozmo's Head and Lift to make it easy to see Cozmo's face'''
        if (self.lift_height.distance_mm > 45) or (self.head_angle.degrees < 40):
            async with self.perform_off_charger():
                lift_action = self.set_lift_height(0.0, in_parallel=True)
                head_action = self.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE,
                                                  in_parallel=True)
                await lift_action.wait_for_completed()
                await head_action.wait_for_completed()

    def display_image_file_on_face(self, image_name):
        # load image and convert it for display on cozmo's face
        image = Image.open(image_name)

        # resize to fit on Cozmo's face screen
        resized_image = image.resize(cozmo.oled_face.dimensions(), Image.NEAREST)

        # convert the image to the format used by the oled screen
        face_image = cozmo.oled_face.convert_image_to_screen_data(resized_image,
                                                                  invert_image=True)

        # display image for 5 seconds
        self.display_oled_face_image(face_image, 5000.0)
