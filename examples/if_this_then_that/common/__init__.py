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
    2) perform_operation_off_charger and backup_onto_charger methods help
        Cozmo return to his charger between If This Then That trigger calls.
    3) display_image_on_face and display_text_on_face methods display the
        requested image file or text, respectively, on his face after
        the If This Then That trigger has been received.
'''

import asyncio
import sys

import cozmo


try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install Pillow` to install")


class IFTTTRobot(cozmo.robot.Robot):
    '''Add some methods to the base Robot class.'''
    async def get_in_position(self):
        '''If necessary, Move Cozmo's Head and Lift to make it easy to see Cozmo's face'''
        if (self.lift_height.distance_mm > 45) or (self.head_angle.degrees < 40):
            async with self.perform_operation_off_charger():
                await self.set_lift_height(0.0).wait_for_completed()
                await self.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

    async def backup_onto_charger(self):
        '''Attempts to reverse robot onto its charger.

        Assumes charger is directly behind Cozmo
        Keep driving straight back until charger is in contact
        '''

        await self.drive_wheels(-30, -30)
        time_waited = 0.0
        while time_waited < 3.0 and not self.is_on_charger:
            sleep_time_s = 0.1
            await asyncio.sleep(sleep_time_s)
            time_waited += sleep_time_s

        self.stop_all_motors()

    def perform_operation_off_charger(self):
        return PerformOffCharger(self)

    def display_image_file_on_face(self, image_name):
        # load image and convert it for display on cozmo's face
        image = Image.open(image_name)

        # resize to fit on Cozmo's face screen
        resized_image = image.resize(cozmo.oled_face.dimensions(), Image.NEAREST)

        self.display_image_on_face(resized_image, True)

    def display_text_on_face(self, text_to_draw, x, y):
        '''Make a PIL.Image with the given text printed on it

        Args:
            text_to_draw (string): the text to draw to the image
            x (int): x pixel location
            y (int): y pixel location
            font (PIL.ImageFont): the font to use

        Returns:
            :class:(`PIL.Image.Image`): a PIL image with the text drawn on it
        '''

        # get a font - location depends on OS so try a couple of options
        # failing that the default of None will just use a default font
        font = None
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            try:
                font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 20)
            except IOError:
                pass

        text_image = Image.new('RGBA', cozmo.oled_face.dimensions(), (0, 0, 0, 255))

        # get a drawing context
        dc = ImageDraw.Draw(text_image)

        # draw the text
        dc.text((x, y), text_to_draw, fill=(255, 255, 255, 255), font=font)

        self.display_image_on_face(text_image, False)

        return text_image

    def display_image_on_face(self, image, invert_image):
        # convert the image to the format used by the oled screen
        face_image = cozmo.oled_face.convert_image_to_screen_data(image,
                                                                  invert_image=invert_image)

        # display image for 5 seconds
        self.display_oled_face_image(face_image, 5000.0)


class PerformOffCharger:
    '''A helper class to provide a context manager to do operations while Cozmo is off charger.'''
    def __init__(self, robot):
        self.robot = robot

    async def __aenter__(self):
        self.was_on_charger = self.robot.is_on_charger
        await self.robot.drive_off_charger_contacts().wait_for_completed()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.was_on_charger:
            await self.robot.backup_onto_charger()
        return False
