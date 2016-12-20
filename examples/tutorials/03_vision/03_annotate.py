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

'''Display a GUI window showing an annotated camera view.

Note:
    This example requires Python to have Tkinter installed to display the GUI.
    It also requires the Pillow and numpy python packages to be pip installed.

The :class:`cozmo.world.World` object collects raw images from Cozmo's camera
and makes them available as a property (:attr:`~cozmo.world.World.latest_image`)
and by generating :class:`cozmo.world.EvtNewCamerImages` events as they come in.

Each image is an instance of :class:`cozmo.world.CameraImage` which provides
access both to the raw camera image, and to a scalable annotated image which
can show where Cozmo sees faces and objects, along with any other information
your program may wish to display.

This example uses the tkviewer to display the annotated camera on the screen
and adds a couple of custom annotations of its own using two different methods.
'''


import sys
import time

try:
    from PIL import ImageDraw, ImageFont
except ImportError:
    sys.exit('run `pip3 install --user Pillow numpy` to run this example')

import cozmo


# Define an annotator using the annotator decorator
@cozmo.annotate.annotator
def clock(image, scale, annotator=None, world=None, **kw):
    d = ImageDraw.Draw(image)
    bounds = (0, 0, image.width, image.height)
    text = cozmo.annotate.ImageText(time.strftime("%H:%m:%S"),
            position=cozmo.annotate.TOP_LEFT)
    text.render(d, bounds)

# Define another decorator as a subclass of Annotator
class Battery(cozmo.annotate.Annotator):
    def apply(self, image, scale):
        d = ImageDraw.Draw(image)
        bounds = (0, 0, image.width, image.height)
        batt = self.world.robot.battery_voltage
        text = cozmo.annotate.ImageText('BATT %.1fv' % batt, color='green')
        text.render(d, bounds)


def cozmo_program(robot: cozmo.robot.Robot):
    robot.world.image_annotator.add_static_text('text', 'Coz-Cam', position=cozmo.annotate.TOP_RIGHT)
    robot.world.image_annotator.add_annotator('clock', clock)
    robot.world.image_annotator.add_annotator('battery', Battery)

    time.sleep(2)

    print("Turning off all annotations for 2 seconds")
    robot.world.image_annotator.annotation_enabled = False
    time.sleep(2)

    print('Re-enabling all annotations')
    robot.world.image_annotator.annotation_enabled = True

    # Disable the face annotator after 10 seconds
    time.sleep(10)
    print("Disabling face annotations (light cubes still annotated)")
    robot.world.image_annotator.disable_annotator('faces')

    # Shutdown the program after 100 seconds
    time.sleep(100)


cozmo.run_program(cozmo_program, use_viewer=True, force_viewer_on_top=True)
