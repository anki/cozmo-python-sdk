#!/usr/bin/env python3

# Copyright (c) 2017 Anki, Inc.
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

'''Demonstrate the manual and auto exposure settings of Cozmo's camera.

This example demonstrates the use of auto exposure and manual exposure for
Cozmo's camera. The current camera settings are overlayed onto the camera
viewer window.
'''


import sys
import time

try:
    from PIL import ImageDraw, ImageFont
    import numpy as np
except ImportError:
    sys.exit('run `pip3 install --user Pillow numpy` to run this example')

import cozmo


# A global string value to display in the camera viewer window to make it more
# obvious what the example program is currently doing.
example_mode = ""


# An annotator for live-display of all of the camera info on top of the camera
# viewer window.
@cozmo.annotate.annotator
def camera_info(image, scale, annotator=None, world=None, **kw):
    d = ImageDraw.Draw(image)
    bounds = [3, 0, image.width, image.height]

    camera = world.robot.camera
    text_to_display = "Example Mode: " + example_mode + "\n\n"
    text_to_display += "Fixed Camera Settings (Calibrated for this Robot):\n\n"
    text_to_display += 'focal_length: %s\n' % camera.config.focal_length
    text_to_display += 'center: %s\n' % camera.config.center
    text_to_display += 'fov: <%.3f, %.3f> degrees\n' % (camera.config.fov_x.degrees,
                                                        camera.config.fov_y.degrees)
    text_to_display += "\n"
    text_to_display += "Valid exposure and gain ranges:\n\n"
    text_to_display += 'exposure: %s..%s\n' % (camera.config.min_exposure_time_ms,
                                               camera.config.max_exposure_time_ms)
    text_to_display += 'gain: %.3f..%.3f\n' % (camera.config.min_gain,
                                               camera.config.max_gain)
    text_to_display += "\n"
    text_to_display += "Current settings:\n\n"
    text_to_display += 'Auto Exposure Enabled: %s\n' % camera.is_auto_exposure_enabled
    text_to_display += 'Exposure: %s ms\n' % camera.exposure_ms
    text_to_display += 'Gain: %.3f\n' % camera.gain
    color_mode_str = "Color" if camera.color_image_enabled else "Grayscale"
    text_to_display += 'Color Mode: %s\n' % color_mode_str

    text = cozmo.annotate.ImageText(text_to_display,
                                    position=cozmo.annotate.TOP_LEFT,
                                    line_spacing=2,
                                    color="white",
                                    outline_color="black", full_outline=True)
    text.render(d, bounds)


def demo_camera_exposure(robot: cozmo.robot.Robot):
    global example_mode

    # Ensure camera is in auto exposure mode and demonstrate auto exposure for 5 seconds
    camera = robot.camera
    camera.enable_auto_exposure()
    example_mode = "Auto Exposure"
    time.sleep(5)

    # Demonstrate manual exposure, linearly increasing the exposure time, while
    # keeping the gain fixed at a medium value.
    example_mode = "Manual Exposure - Increasing Exposure, Fixed Gain"
    fixed_gain = (camera.config.min_gain + camera.config.max_gain) * 0.5
    for exposure in range(camera.config.min_exposure_time_ms, camera.config.max_exposure_time_ms+1, 1):
        camera.set_manual_exposure(exposure, fixed_gain)
        time.sleep(0.1)

    # Demonstrate manual exposure, linearly increasing the gain, while keeping
    # the exposure fixed at a relatively low value.
    example_mode = "Manual Exposure - Increasing Gain, Fixed Exposure"
    fixed_exposure_ms = 10
    for gain in np.arange(camera.config.min_gain, camera.config.max_gain, 0.05):
        camera.set_manual_exposure(fixed_exposure_ms, gain)
        time.sleep(0.1)

    # Switch back to auto exposure, demo for a final 5 seconds and then return
    camera.enable_auto_exposure()
    example_mode = "Mode: Auto Exposure"
    time.sleep(5)


def cozmo_program(robot: cozmo.robot.Robot):
    robot.world.image_annotator.add_annotator('camera_info', camera_info)

    # Demo with default grayscale camera images
    robot.camera.color_image_enabled = False
    demo_camera_exposure(robot)

    # Demo with color camera images
    robot.camera.color_image_enabled = True
    demo_camera_exposure(robot)


cozmo.robot.Robot.drive_off_charger_on_connect = False  # Cozmo can stay on his charger for this example
cozmo.run_program(cozmo_program, use_viewer=True, force_viewer_on_top=True)
