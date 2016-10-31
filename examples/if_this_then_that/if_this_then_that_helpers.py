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

'''If This Then That helper class

Wrapper class for integrating Cozmo with If This Then That (http://ifttt.com).
See ifttt_gmail.py for an example of this class being used.

This class includes:
    1) method get_in_position to move Cozmo's lift down and face up if necessary
    2) method perform_operation_off_charger and backup_onto_charger so that Cozmo
        can return to his charger between If This Then That trigger calls
    3) method display_image_on_face to display the requested image on his face after
        the If This Then That trigger has been received
    4) a queue to store If This Then That trigger calls as they come in
'''

from contextlib import contextmanager
import queue
import sys
import threading
import time

import cozmo


try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install Pillow` to install")

class IfThisThenThatHelper:

    def __init__(self, coz):
        self.cozmo = coz
        self.queue = queue.Queue()

        '''Start a separate thread to check if the queue contains an action to run.'''
        threading.Thread(target=self.worker).start()

        self.get_in_position(self.cozmo)


    def get_in_position(self, robot):
        '''If necessary, Move Cozmo'qs Head and Lift to make it easy to see Cozmo's face'''
        if (robot.lift_height.distance_mm > 45) or (robot.head_angle.degrees < 40):
            with self.perform_operation_off_charger(robot):
                robot.set_lift_height(0.0).wait_for_completed()
                robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()


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
        If Cozmo started on the charger then return it back afterwards.
        '''
        was_on_charger = robot.is_on_charger
        robot.drive_off_charger_contacts().wait_for_completed()

        yield robot

        if was_on_charger:
            self.backup_onto_charger(robot)


    def display_image_file_on_face(self, image_name):
        # load image and convert it for display on cozmo's face
        image = Image.open(image_name)

        self.display_image_on_face(image)


    def display_image_on_face(self, image):
        # resize to fit on Cozmo's face screen
        resized_image = image.resize(cozmo.oled_face.dimensions(), Image.NEAREST)

        # convert the image to the format used by the oled screen
        face_image = cozmo.oled_face.convert_image_to_screen_data(resized_image,
                                                                  invert_image=True)

        # display image for 5 seconds
        self.cozmo.display_oled_face_image(face_image, 5000.0)
