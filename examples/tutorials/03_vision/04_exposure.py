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

    camera_config = world.robot.camera_config
    text_to_display = "Example Mode: " + example_mode + "\n\n"
    text_to_display += "Fixed Camera Settings (Calibrated for this Robot):\n\n"
    text_to_display += 'focal_length: %s\n' % camera_config.focal_length
    text_to_display += 'center: %s\n' % camera_config.center
    text_to_display += 'fov: <%.3f, %.3f> degrees\n' % (camera_config.fov_x.degrees,
                                                        camera_config.fov_y.degrees)
    text_to_display += "\n"
    text_to_display += "Valid exposure and gain ranges:\n\n"
    text_to_display += 'exposure: %s..%s\n' % (camera_config.min_exposure_time_ms,
                                               camera_config.max_exposure_time_ms)
    text_to_display += 'gain: %.3f..%.3f\n' % (camera_config.min_camera_gain,
                                               camera_config.max_camera_gain)
    text_to_display += "\n"
    text_to_display += "Current settings:\n\n"
    text_to_display += 'Auto Exposure Enabled: %s\n' % camera_config.is_auto_exposure_enabled
    text_to_display += 'Exposure: %s ms\n' % camera_config.exposure_ms
    text_to_display += 'Gain: %.3f\n' % camera_config.camera_gain

    text = cozmo.annotate.ImageText(text_to_display,
                                    position=cozmo.annotate.TOP_LEFT,
                                    line_spacing=2,
                                    color="white",
                                    outline_color="black", full_outline=True)
    text.render(d, bounds)


def cozmo_program(robot: cozmo.robot.Robot):
    global example_mode
    robot.world.image_annotator.add_annotator('camera_info', camera_info)

    # Ensure camera is in auto exposure mode and demonstrate auto exposure for 5 seconds
    robot.enable_auto_exposure()
    example_mode = "Auto Exposure"
    time.sleep(5)

    # Grab the current auto exposure/gain values as good defaults for
    # the current lighting conditions
    cam = robot.camera_config
    auto_exposure_ms = cam.exposure_ms
    auto_gain = cam.camera_gain

    # Demonstrate manual exposure, linearly increasing the exposure time
    example_mode = "Manual Exposure - Increasing Exposure, Fixed Gain"
    for exposure in range(cam.min_exposure_time_ms, cam.max_exposure_time_ms+1, 1):
        robot.set_manual_exposure(exposure, auto_gain)
        time.sleep(0.1)

    # Demonstrate manual exposure, linearly increasing the gain
    example_mode = "Manual Exposure - Increasing Gain, Fixed Exposure"
    for gain in np.arange(cam.min_camera_gain, cam.max_camera_gain, 0.05):
        robot.set_manual_exposure(auto_exposure_ms, gain)
        time.sleep(0.1)

    # Switch back to auto exposure, demo for a final 5 seconds and then exit
    robot.enable_auto_exposure()
    example_mode = "Mode: Auto Exposure"
    time.sleep(5)


cozmo.run_program(cozmo_program, use_viewer=True, force_viewer_on_top=True)
