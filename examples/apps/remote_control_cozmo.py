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

'''Control Cozmo using a webpage on your computer.

This example lets you control Cozmo by Remote Control, using a webpage served by Flask.
'''

import asyncio
import io
import json
import math
import sys

sys.path.append('../lib/')
import flask_helpers
import cozmo


try:
    from flask import Flask, request
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install --user flask` to install")

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

try:
    import requests
except ImportError:
    sys.exit("Cannot import from requests: Do `pip3 install --user requests` to install")


DEBUG_ANNOTATIONS_DISABLED = 0
DEBUG_ANNOTATIONS_ENABLED_VISION = 1
DEBUG_ANNOTATIONS_ENABLED_ALL = 2


# Annotator for displaying RobotState (position, etc.) on top of the camera feed
class RobotStateDisplay(cozmo.annotate.Annotator):
    def apply(self, image, scale):
        d = ImageDraw.Draw(image)

        bounds = [3, 0, image.width, image.height]

        def print_line(text_line):
            text = cozmo.annotate.ImageText(text_line, position=cozmo.annotate.TOP_LEFT, outline_color='black', color='lightblue')
            text.render(d, bounds)
            TEXT_HEIGHT = 11
            bounds[1] += TEXT_HEIGHT

        robot = self.world.robot  # type: cozmo.robot.Robot

        # Display the Pose info for the robot

        pose = robot.pose
        print_line('Pose: Pos = <%.1f, %.1f, %.1f>' % pose.position.x_y_z)
        print_line('Pose: Rot quat = <%.1f, %.1f, %.1f, %.1f>' % pose.rotation.q0_q1_q2_q3)
        print_line('Pose: angle_z = %.1f' % pose.rotation.angle_z.degrees)
        print_line('Pose: origin_id: %s' % pose.origin_id)

        # Display the Accelerometer and Gyro data for the robot

        print_line('Accelmtr: <%.1f, %.1f, %.1f>' % robot.accelerometer.x_y_z)
        print_line('Gyro: <%.1f, %.1f, %.1f>' % robot.gyro.x_y_z)

        # Display the Accelerometer and Gyro data for the mobile device

        if robot.device_accel_raw is not None:
            print_line('Device Acc Raw: <%.2f, %.2f, %.2f>' % robot.device_accel_raw.x_y_z)
        if robot.device_accel_user is not None:
            print_line('Device Acc User: <%.2f, %.2f, %.2f>' % robot.device_accel_user.x_y_z)
        if robot.device_gyro is not None:
            mat = robot.device_gyro.to_matrix()
            print_line('Device Gyro Up: <%.2f, %.2f, %.2f>' % mat.up_xyz)
            print_line('Device Gyro Fwd: <%.2f, %.2f, %.2f>' % mat.forward_xyz)
            print_line('Device Gyro Left: <%.2f, %.2f, %.2f>' % mat.left_xyz)


def create_default_image(image_width, image_height, do_gradient=False):
    '''Create a place-holder PIL image to use until we have a live feed from Cozmo'''
    image_bytes = bytearray([0x70, 0x70, 0x70]) * image_width * image_height

    if do_gradient:
        i = 0
        for y in range(image_height):
            for x in range(image_width):
                image_bytes[i] = int(255.0 * (x / image_width))   # R
                image_bytes[i+1] = int(255.0 * (y / image_height))  # G
                image_bytes[i+2] = 0                                # B
                i += 3

    image = Image.frombytes('RGB', (image_width, image_height), bytes(image_bytes))
    return image


flask_app = Flask(__name__)
remote_control_cozmo = None
_default_camera_image = create_default_image(320, 240)
_is_mouse_look_enabled_by_default = False
_is_device_gyro_mode_enabled_by_default = False
_gyro_driving_deadzone_ratio = 0.025

_display_debug_annotations = DEBUG_ANNOTATIONS_ENABLED_ALL


def remap_to_range(x, x_min, x_max, out_min, out_max):
    '''convert x (in x_min..x_max range) to out_min..out_max range'''
    if x < x_min:
        return out_min
    elif x > x_max:
        return out_max
    else:
        ratio = (x - x_min) / (x_max - x_min)
        return out_min + ratio * (out_max - out_min)


class RemoteControlCozmo:

    def __init__(self, coz):
        self.cozmo = coz

        self.drive_forwards = 0
        self.drive_back = 0
        self.turn_left = 0
        self.turn_right = 0
        self.lift_up = 0
        self.lift_down = 0
        self.head_up = 0
        self.head_down = 0

        self.go_fast = 0
        self.go_slow = 0

        self.is_mouse_look_enabled = _is_mouse_look_enabled_by_default
        self.is_device_gyro_mode_enabled = _is_device_gyro_mode_enabled_by_default
        self.mouse_dir = 0

        all_anim_names = list(self.cozmo.anim_names)
        all_anim_names.sort()
        self.anim_names = []

        # Hide a few specific test animations that don't behave well
        bad_anim_names = [
            "ANIMATION_TEST",
            "soundTestAnim"]

        for anim_name in all_anim_names:
            if anim_name not in bad_anim_names:
                self.anim_names.append(anim_name)

        default_anims_for_keys = ["anim_bored_01",  # 0
                                  "anim_poked_giggle",  # 1
                                  "anim_pounce_success_02",  # 2
                                  "anim_bored_event_02",  # 3
                                  "anim_bored_event_03",  # 4
                                  "anim_petdetection_cat_01",  # 5
                                  "anim_petdetection_dog_03",  # 6
                                  "anim_reacttoface_unidentified_02",  # 7
                                  "anim_upgrade_reaction_lift_01",  # 8
                                  "anim_speedtap_wingame_intensity02_01"  # 9
                                 ]

        self.anim_index_for_key = [0] * 10
        kI = 0
        for default_key in default_anims_for_keys:
            try:
                anim_idx = self.anim_names.index(default_key)
            except ValueError:
                print("Error: default_anim %s is not in the list of animations" % default_key)
                anim_idx = kI
            self.anim_index_for_key[kI] = anim_idx
            kI += 1


        self.action_queue = []
        self.text_to_say = "Hi I'm Cozmo"


    def set_anim(self, key_index, anim_index):
        self.anim_index_for_key[key_index] = anim_index


    def handle_mouse(self, mouse_x, mouse_y, delta_x, delta_y, is_button_down):
        '''Called whenever mouse moves
            mouse_x, mouse_y are in in 0..1 range (0,0 = top left, 1,1 = bottom right of window)
            delta_x, delta_y are the change in mouse_x/y since the last update
        '''
        if self.is_mouse_look_enabled:
            mouse_sensitivity = 1.5 # higher = more twitchy
            self.mouse_dir = remap_to_range(mouse_x, 0.0, 1.0, -mouse_sensitivity, mouse_sensitivity)
            self.update_mouse_driving()

            desired_head_angle = remap_to_range(mouse_y, 0.0, 1.0, 45, -25)
            head_angle_delta = desired_head_angle - self.cozmo.head_angle.degrees
            head_vel = head_angle_delta * 0.03
            self.cozmo.move_head(head_vel)


    def set_mouse_look_enabled(self, is_mouse_look_enabled):
        was_mouse_look_enabled = self.is_mouse_look_enabled
        self.is_mouse_look_enabled = is_mouse_look_enabled
        if not is_mouse_look_enabled:
            # cancel any current mouse-look turning
            self.mouse_dir = 0
            if was_mouse_look_enabled:
                self.update_mouse_driving()
                self.update_head()


    def handle_key(self, key_code, is_shift_down, is_ctrl_down, is_alt_down, is_key_down):
        '''Called on any key press or release
           Holding a key down may result in repeated handle_key calls with is_key_down==True
        '''

        # Update desired speed / fidelity of actions based on shift/alt being held
        was_go_fast = self.go_fast
        was_go_slow = self.go_slow

        self.go_fast = is_shift_down
        self.go_slow = is_alt_down

        speed_changed = (was_go_fast != self.go_fast) or (was_go_slow != self.go_slow)

        # Update state of driving intent from keyboard, and if anything changed then call update_driving
        update_driving = True
        if key_code == ord('W'):
            self.drive_forwards = is_key_down
        elif key_code == ord('S'):
            self.drive_back = is_key_down
        elif key_code == ord('A'):
            self.turn_left = is_key_down
        elif key_code == ord('D'):
            self.turn_right = is_key_down
        else:
            if not speed_changed:
                update_driving = False

        # Update state of lift move intent from keyboard, and if anything changed then call update_lift
        update_lift = True
        if key_code == ord('R'):
            self.lift_up = is_key_down
        elif key_code == ord('F'):
            self.lift_down = is_key_down
        else:
            if not speed_changed:
                update_lift = False

        # Update state of head move intent from keyboard, and if anything changed then call update_head
        update_head = True
        if key_code == ord('T'):
            self.head_up = is_key_down
        elif key_code == ord('G'):
            self.head_down = is_key_down
        else:
            if not speed_changed:
                update_head = False

        # Update driving, head and lift as appropriate
        if update_driving:
            self.update_mouse_driving()
        if update_head:
            self.update_head()
        if update_lift:
            self.update_lift()

        # Handle any keys being released (e.g. the end of a key-click)
        if not is_key_down:
            if (key_code >= ord('0')) and (key_code <= ord('9')):
                anim_name = self.key_code_to_anim_name(key_code)
                self.play_animation(anim_name)
            elif key_code == ord(' '):
                self.say_text(self.text_to_say)


    def key_code_to_anim_name(self, key_code):
        key_num = key_code - ord('0')
        anim_num = self.anim_index_for_key[key_num]
        anim_name = self.anim_names[anim_num]
        return anim_name


    def func_to_name(self, func):
        if func == self.try_say_text:
            return "say_text"
        elif func == self.try_play_anim:
            return "play_anim"
        else:
            return "UNKNOWN"


    def action_to_text(self, action):
        func, args = action
        return self.func_to_name(func) + "( " + str(args) + " )"


    def action_queue_to_text(self, action_queue):
        out_text = ""
        i = 0
        for action in action_queue:
            out_text += "[" + str(i) + "] " + self.action_to_text(action)
            i += 1
        return out_text


    def queue_action(self, new_action):
        if len(self.action_queue) > 10:
            self.action_queue.pop(0)
        self.action_queue.append(new_action)


    def try_say_text(self, text_to_say):
        try:
            self.cozmo.say_text(text_to_say)
            return True
        except cozmo.exceptions.RobotBusy:
            return False


    def try_play_anim(self, anim_name):
        try:
            self.cozmo.play_anim(name=anim_name)
            return True
        except cozmo.exceptions.RobotBusy:
            return False


    def say_text(self, text_to_say):
        self.queue_action((self.try_say_text, text_to_say))
        self.update()


    def play_animation(self, anim_name):
        self.queue_action((self.try_play_anim, anim_name))
        self.update()


    def update(self):
        '''Try and execute the next queued action'''
        if len(self.action_queue) > 0:
            queued_action, action_args = self.action_queue[0]
            if queued_action(action_args):
                self.action_queue.pop(0)
        # Update gyro
        if self.is_device_gyro_mode_enabled and self.cozmo.device_gyro:
            self.update_gyro_driving()


    def pick_speed(self, fast_speed, mid_speed, slow_speed):
        if self.go_fast:
            if not self.go_slow:
                return fast_speed
        elif self.go_slow:
            return slow_speed
        return mid_speed


    def update_lift(self):
        lift_speed = self.pick_speed(8, 4, 2)
        lift_vel = (self.lift_up - self.lift_down) * lift_speed
        self.cozmo.move_lift(lift_vel)


    def update_head(self):
        if not self.is_mouse_look_enabled:
            head_speed = self.pick_speed(2, 1, 0.5)
            head_vel = (self.head_up - self.head_down) * head_speed
            self.cozmo.move_head(head_vel)

    def scale_deadzone(self, value, deadzone, maximum):
        if math.fabs(value) > deadzone:
            adjustment = math.copysign(deadzone, value)
            scaleFactor = maximum / (maximum - deadzone)
            return (value - adjustment) * scaleFactor
        else:
            return 0

    def update_gyro_driving(self):
        pitch, yaw, roll = self.cozmo.device_gyro.euler_angles
        # these are multiplied by 2 because 90 degress feels better for full velocity than 180 degrees
        drive_dir = self.scale_deadzone(pitch/math.pi, _gyro_driving_deadzone_ratio, 1) * 2
        turn_dir = self.scale_deadzone(roll/math.pi, _gyro_driving_deadzone_ratio, 1) * 2

        forward_speed = 250
        turn_speed = 250
        wheel_acceleration = 250

        l_wheel_speed = (drive_dir * forward_speed) + (turn_speed * turn_dir)
        r_wheel_speed = (drive_dir * forward_speed) - (turn_speed * turn_dir)

        self.cozmo.drive_wheels(l_wheel_speed, r_wheel_speed, wheel_acceleration, wheel_acceleration)

    def update_mouse_driving(self):
        drive_dir = (self.drive_forwards - self.drive_back)

        if (drive_dir > 0.1) and self.cozmo.is_on_charger:
            # cozmo is stuck on the charger, and user is trying to drive off - issue an explicit drive off action
            try:
                # don't wait for action to complete - we don't want to block the other updates (camera etc.)
                self.cozmo.drive_off_charger_contacts()
            except cozmo.exceptions.RobotBusy:
                # Robot is busy doing another action - try again next time we get a drive impulse
                pass

        turn_dir = (self.turn_right - self.turn_left) + self.mouse_dir
        if drive_dir < 0:
            # It feels more natural to turn the opposite way when reversing
            turn_dir = -turn_dir

        forward_speed = self.pick_speed(150, 75, 50)
        turn_speed = self.pick_speed(100, 50, 30)

        l_wheel_speed = (drive_dir * forward_speed) + (turn_speed * turn_dir)
        r_wheel_speed = (drive_dir * forward_speed) - (turn_speed * turn_dir)

        self.cozmo.drive_wheels(l_wheel_speed, r_wheel_speed, l_wheel_speed*4, r_wheel_speed*4 )

def get_anim_sel_drop_down(selectorIndex):
    html_text = '''<select onchange="handleDropDownSelect(this)" name="animSelector''' + str(selectorIndex) + '''">'''
    i = 0
    for anim_name in remote_control_cozmo.anim_names:
        is_selected_item = (i == remote_control_cozmo.anim_index_for_key[selectorIndex])
        selected_text = ''' selected="selected"''' if is_selected_item else ""
        html_text += '''<option value=''' + str(i) + selected_text + '''>''' + anim_name + '''</option>'''
        i += 1
    html_text += '''</select>'''
    return html_text


def get_anim_sel_drop_downs():
    html_text = ""
    for i in range(10):
        # list keys 1..9,0 as that's the layout on the keyboard
        key = i+1 if (i<9) else 0
        html_text += str(key) + ''': ''' + get_anim_sel_drop_down(key) + '''<br>'''
    return html_text


def to_js_bool_string(bool_value):
    return "true" if bool_value else "false"


@flask_app.route("/")
def handle_index_page():
    return '''
    <html>
        <head>
            <title>remote_control_cozmo.py display</title>
        </head>
        <body>
            <h1>Remote Control Cozmo</h1>
            <table>
                <tr>
                    <td valign = top>
                        <div id="cozmoImageMicrosoftWarning" style="display: none;color: #ff9900; text-align: center;">Video feed performance is better in Chrome or Firefox due to mjpeg limitations in this browser</div>
                        <img src="cozmoImage" id="cozmoImageId" width=640 height=480>
                        <div id="DebugInfoId"></div>
                    </td>
                    <td width=30></td>
                    <td valign=top>
                        <h2>Controls:</h2>

                        <h3>Driving:</h3>

                        <b>W A S D</b> : Drive Forwards / Left / Back / Right<br><br>
                        <b>Q</b> : Toggle Mouse Look: <button id="mouseLookId" onClick=onMouseLookButtonClicked(this) style="font-size: 14px">Default</button><br>
                        <b>Mouse</b> : Move in browser window to aim<br>
                        (steer and head angle)<br>
                        (similar to an FPS game)<br>
                        <br>
                        <b>T</b> : Move Head Up<br>
                        <b>G</b> : Move Head Down<br>

                        <h3>Lift:</h3>
                        <b>R</b> : Move Lift Up<br>
                        <b>F</b>: Move Lift Down<br>
                        <h3>General:</h3>
                        <b>Shift</b> : Hold to Move Faster (Driving, Head and Lift)<br>
                        <b>Alt</b> : Hold to Move Slower (Driving, Head and Lift)<br>
                        <b>L</b> : Toggle IR Headlight: <button id="headlightId" onClick=onHeadlightButtonClicked(this) style="font-size: 14px">Default</button><br>
                        <b>O</b> : Toggle Debug Annotations: <button id="debugAnnotationsId" onClick=onDebugAnnotationsButtonClicked(this) style="font-size: 14px">Default</button><br>
                        <b>P</b> : Toggle Free Play mode: <button id="freeplayId" onClick=onFreeplayButtonClicked(this) style="font-size: 14px">Default</button><br>
                        <b>Y</b> : Toggle Device Gyro mode: <button id="deviceGyroId" onClick=onDeviceGyroButtonClicked(this) style="font-size: 14px">Default</button><br>
                        <h3>Play Animations</h3>
                        <b>0 .. 9</b> : Play Animation mapped to that key<br>
                        <h3>Talk</h3>
                        <b>Space</b> : Say <input type="text" name="sayText" id="sayTextId" value="''' + remote_control_cozmo.text_to_say + '''" onchange=handleTextInput(this)>
                    </td>
                    <td width=30></td>
                    <td valign=top>
                    <h2>Animation key mappings:</h2>
                    ''' + get_anim_sel_drop_downs() + '''<br>
                    </td>
                </tr>
            </table>

            <script type="text/javascript">
                var gLastClientX = -1
                var gLastClientY = -1
                var gIsMouseLookEnabled = '''+ to_js_bool_string(_is_mouse_look_enabled_by_default) + '''
                var gAreDebugAnnotationsEnabled = '''+ str(_display_debug_annotations) + '''
                var gIsHeadlightEnabled = false
                var gIsFreeplayEnabled = false
                var gIsDeviceGyroEnabled = false
                var gUserAgent = window.navigator.userAgent;
                var gIsMicrosoftBrowser = gUserAgent.indexOf('MSIE ') > 0 || gUserAgent.indexOf('Trident/') > 0 || gUserAgent.indexOf('Edge/') > 0;
                var gSkipFrame = false;

                if (gIsMicrosoftBrowser) {
                    document.getElementById("cozmoImageMicrosoftWarning").style.display = "block";
                }

                function postHttpRequest(url, dataSet)
                {
                    var xhr = new XMLHttpRequest();
                    xhr.open("POST", url, true);
                    xhr.send( JSON.stringify( dataSet ) );
                }

                function updateCozmo()
                {
                    if (gIsMicrosoftBrowser && !gSkipFrame) {
                        // IE doesn't support MJPEG, so we need to ping the server for more images.
                        // Though, if this happens too frequently, the controls will be unresponsive.
                        gSkipFrame = true;
                        document.getElementById("cozmoImageId").src="cozmoImage?" + (new Date()).getTime();
                    } else if (gSkipFrame) {
                        gSkipFrame = false;
                    }
                    var xhr = new XMLHttpRequest();
                    xhr.onreadystatechange = function() {
                        if (xhr.readyState == XMLHttpRequest.DONE) {
                            document.getElementById("DebugInfoId").innerHTML = xhr.responseText
                        }
                    }

                    xhr.open("POST", "updateCozmo", true);
                    xhr.send( null );
                    setTimeout(updateCozmo , 60);
                }
                setTimeout(updateCozmo , 60);

                function updateButtonEnabledText(button, isEnabled)
                {
                    button.firstChild.data = isEnabled ? "Enabled" : "Disabled";
                }

                function onMouseLookButtonClicked(button)
                {
                    gIsMouseLookEnabled = !gIsMouseLookEnabled;
                    updateButtonEnabledText(button, gIsMouseLookEnabled);
                    isMouseLookEnabled = gIsMouseLookEnabled
                    postHttpRequest("setMouseLookEnabled", {isMouseLookEnabled})
                }

                function updateDebugAnnotationButtonEnabledText(button, isEnabled)
                {
                    switch(gAreDebugAnnotationsEnabled)
                    {
                    case 0:
                        button.firstChild.data = "Disabled";
                        break;
                    case 1:
                        button.firstChild.data = "Enabled (vision)";
                        break;
                    case 2:
                        button.firstChild.data = "Enabled (all)";
                        break;
                    default:
                        button.firstChild.data = "ERROR";
                        break;
                    }
                }

                function onDebugAnnotationsButtonClicked(button)
                {
                    gAreDebugAnnotationsEnabled += 1;
                    if (gAreDebugAnnotationsEnabled > 2)
                    {
                        gAreDebugAnnotationsEnabled = 0
                    }

                    updateDebugAnnotationButtonEnabledText(button, gAreDebugAnnotationsEnabled)

                    areDebugAnnotationsEnabled = gAreDebugAnnotationsEnabled
                    postHttpRequest("setAreDebugAnnotationsEnabled", {areDebugAnnotationsEnabled})
                }

                function onHeadlightButtonClicked(button)
                {
                    gIsHeadlightEnabled = !gIsHeadlightEnabled;
                    updateButtonEnabledText(button, gIsHeadlightEnabled);
                    isHeadlightEnabled = gIsHeadlightEnabled
                    postHttpRequest("setHeadlightEnabled", {isHeadlightEnabled})
                }

                function onFreeplayButtonClicked(button)
                {
                    gIsFreeplayEnabled = !gIsFreeplayEnabled;
                    updateButtonEnabledText(button, gIsFreeplayEnabled);
                    isFreeplayEnabled = gIsFreeplayEnabled
                    postHttpRequest("setFreeplayEnabled", {isFreeplayEnabled})
                }

                function onDeviceGyroButtonClicked(button)
                {
                    gIsDeviceGyroEnabled = !gIsDeviceGyroEnabled;
                    updateButtonEnabledText(button, gIsDeviceGyroEnabled);
                    isDeviceGyroEnabled = gIsDeviceGyroEnabled
                    postHttpRequest("setDeviceGyroEnabled", {isDeviceGyroEnabled})
                }

                updateButtonEnabledText(document.getElementById("mouseLookId"), gIsMouseLookEnabled);
                updateButtonEnabledText(document.getElementById("headlightId"), gIsHeadlightEnabled);
                updateDebugAnnotationButtonEnabledText(document.getElementById("debugAnnotationsId"), gAreDebugAnnotationsEnabled);
                updateButtonEnabledText(document.getElementById("freeplayId"), gIsFreeplayEnabled);
                updateButtonEnabledText(document.getElementById("deviceGyroId"), gIsDeviceGyroEnabled);

                function handleDropDownSelect(selectObject)
                {
                    selectedIndex = selectObject.selectedIndex
                    itemName = selectObject.name
                    postHttpRequest("dropDownSelect", {selectedIndex, itemName});
                }

                function handleKeyActivity (e, actionType)
                {
                    var keyCode  = (e.keyCode ? e.keyCode : e.which);
                    var hasShift = (e.shiftKey ? 1 : 0)
                    var hasCtrl  = (e.ctrlKey  ? 1 : 0)
                    var hasAlt   = (e.altKey   ? 1 : 0)

                    if (actionType=="keyup")
                    {
                        if (keyCode == 76) // 'L'
                        {
                            // Simulate a click of the headlight button
                            onHeadlightButtonClicked(document.getElementById("headlightId"))
                        }
                        else if (keyCode == 79) // 'O'
                        {
                            // Simulate a click of the debug annotations button
                            onDebugAnnotationsButtonClicked(document.getElementById("debugAnnotationsId"))
                        }
                        else if (keyCode == 80) // 'P'
                        {
                            // Simulate a click of the debug annotations button
                            onFreeplayButtonClicked(document.getElementById("freeplayId"))
                        }
                        else if (keyCode == 81) // 'Q'
                        {
                            // Simulate a click of the mouse look button
                            onMouseLookButtonClicked(document.getElementById("mouseLookId"))
                        }
                        else if (keyCode == 89) // 'Y'
                        {
                            // Simulate a click of the device gyro button
                            onDeviceGyroButtonClicked(document.getElementById("deviceGyroId"))
                        }
                    }

                    postHttpRequest(actionType, {keyCode, hasShift, hasCtrl, hasAlt})
                }

                function handleMouseActivity (e, actionType)
                {
                    var clientX = e.clientX / document.body.clientWidth  // 0..1 (left..right)
                    var clientY = e.clientY / document.body.clientHeight // 0..1 (top..bottom)
                    var isButtonDown = e.which && (e.which != 0) ? 1 : 0
                    var deltaX = (gLastClientX >= 0) ? (clientX - gLastClientX) : 0.0
                    var deltaY = (gLastClientY >= 0) ? (clientY - gLastClientY) : 0.0
                    gLastClientX = clientX
                    gLastClientY = clientY

                    postHttpRequest(actionType, {clientX, clientY, isButtonDown, deltaX, deltaY})
                }

                function handleTextInput(textField)
                {
                    textEntered = textField.value
                    postHttpRequest("sayText", {textEntered})
                }

                document.addEventListener("keydown", function(e) { handleKeyActivity(e, "keydown") } );
                document.addEventListener("keyup",   function(e) { handleKeyActivity(e, "keyup") } );

                document.addEventListener("mousemove",   function(e) { handleMouseActivity(e, "mousemove") } );

                function stopEventPropagation(event)
                {
                    if (event.stopPropagation)
                    {
                        event.stopPropagation();
                    }
                    else
                    {
                        event.cancelBubble = true
                    }
                }

                document.getElementById("sayTextId").addEventListener("keydown", function(event) {
                    stopEventPropagation(event);
                } );
                document.getElementById("sayTextId").addEventListener("keyup", function(event) {
                    stopEventPropagation(event);
                } );
            </script>

        </body>
    </html>
    '''

def get_annotated_image():
    image = remote_control_cozmo.cozmo.world.latest_image
    if _display_debug_annotations != DEBUG_ANNOTATIONS_DISABLED:
        image = image.annotate_image(scale=2)
    else:
        image = image.raw_image
    return image

def streaming_video(url_root):
    '''Video streaming generator function'''
    try:
        while True:
            if remote_control_cozmo:
                image = get_annotated_image()

                img_io = io.BytesIO()
                image.save(img_io, 'PNG')
                img_io.seek(0)
                yield (b'--frame\r\n'
                    b'Content-Type: image/png\r\n\r\n' + img_io.getvalue() + b'\r\n')
            else:
                asyncio.sleep(.1)
    except cozmo.exceptions.SDKShutdown:
        # Tell the main flask thread to shutdown
        requests.post(url_root + 'shutdown')

def serve_single_image():
    if remote_control_cozmo:
        try:
            image = get_annotated_image()
            if image:
                return flask_helpers.serve_pil_image(image)
        except cozmo.exceptions.SDKShutdown:
            requests.post('shutdown')
    return flask_helpers.serve_pil_image(_default_camera_image)

def is_microsoft_browser(request):
    agent = request.user_agent.string
    return 'Edge/' in agent or 'MSIE ' in agent or 'Trident/' in agent

@flask_app.route("/cozmoImage")
def handle_cozmoImage():
    if is_microsoft_browser(request):
        return serve_single_image()
    return flask_helpers.stream_video(streaming_video, request.url_root)

def handle_key_event(key_request, is_key_down):
    message = json.loads(key_request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.handle_key(key_code=(message['keyCode']), is_shift_down=message['hasShift'],
                                        is_ctrl_down=message['hasCtrl'], is_alt_down=message['hasAlt'],
                                        is_key_down=is_key_down)
    return ""

@flask_app.route('/shutdown', methods=['POST'])
def shutdown():
    flask_helpers.shutdown_flask(request)
    return ""

@flask_app.route('/mousemove', methods=['POST'])
def handle_mousemove():
    '''Called from Javascript whenever mouse moves'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.handle_mouse(mouse_x=(message['clientX']), mouse_y=message['clientY'],
                                          delta_x=message['deltaX'], delta_y=message['deltaY'],
                                          is_button_down=message['isButtonDown'])
    return ""


@flask_app.route('/setMouseLookEnabled', methods=['POST'])
def handle_setMouseLookEnabled():
    '''Called from Javascript whenever mouse-look mode is toggled'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.set_mouse_look_enabled(is_mouse_look_enabled=message['isMouseLookEnabled'])
    return ""


@flask_app.route('/setHeadlightEnabled', methods=['POST'])
def handle_setHeadlightEnabled():
    '''Called from Javascript whenever headlight is toggled on/off'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.cozmo.set_head_light(enable=message['isHeadlightEnabled'])
    return ""


@flask_app.route('/setAreDebugAnnotationsEnabled', methods=['POST'])
def handle_setAreDebugAnnotationsEnabled():
    '''Called from Javascript whenever debug-annotations mode is toggled'''
    message = json.loads(request.data.decode("utf-8"))
    global _display_debug_annotations
    _display_debug_annotations = message['areDebugAnnotationsEnabled']
    if remote_control_cozmo:
        if _display_debug_annotations == DEBUG_ANNOTATIONS_ENABLED_ALL:
            remote_control_cozmo.cozmo.world.image_annotator.enable_annotator('robotState')
        else:
            remote_control_cozmo.cozmo.world.image_annotator.disable_annotator('robotState')
    return ""


@flask_app.route('/setFreeplayEnabled', methods=['POST'])
def handle_setFreeplayEnabled():
    '''Called from Javascript whenever freeplay mode is toggled on/off'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        isFreeplayEnabled = message['isFreeplayEnabled']
        if isFreeplayEnabled:
            remote_control_cozmo.cozmo.start_freeplay_behaviors()
        else:
            remote_control_cozmo.cozmo.stop_freeplay_behaviors()
    return ""


@flask_app.route('/setDeviceGyroEnabled', methods=['POST'])
def handle_setDeviceGyroEnabled():
    '''Called from Javascript whenever device gyro mode is toggled on/off'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        is_device_gyro_enabled = message['isDeviceGyroEnabled']
        if is_device_gyro_enabled:
            remote_control_cozmo.is_device_gyro_mode_enabled = True
        else:
            remote_control_cozmo.is_device_gyro_mode_enabled = False
            # stop movement when turning off gyro mode
            remote_control_cozmo.cozmo.drive_wheels(0, 0, 0, 0)
    return ""


@flask_app.route('/keydown', methods=['POST'])
def handle_keydown():
    '''Called from Javascript whenever a key is down (note: can generate repeat calls if held down)'''
    return handle_key_event(request, is_key_down=True)


@flask_app.route('/keyup', methods=['POST'])
def handle_keyup():
    '''Called from Javascript whenever a key is released'''
    return handle_key_event(request, is_key_down=False)


@flask_app.route('/dropDownSelect', methods=['POST'])
def handle_dropDownSelect():
    '''Called from Javascript whenever an animSelector dropdown menu is selected (i.e. modified)'''
    message = json.loads(request.data.decode("utf-8"))

    item_name_prefix = "animSelector"
    item_name = message['itemName']

    if remote_control_cozmo and item_name.startswith(item_name_prefix):
        item_name_index = int(item_name[len(item_name_prefix):])
        remote_control_cozmo.set_anim(item_name_index, message['selectedIndex'])

    return ""


@flask_app.route('/sayText', methods=['POST'])
def handle_sayText():
    '''Called from Javascript whenever the saytext text field is modified'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.text_to_say = message['textEntered']
    return ""


@flask_app.route('/updateCozmo', methods=['POST'])
def handle_updateCozmo():
    if remote_control_cozmo:
        remote_control_cozmo.update()
        action_queue_text = ""
        i = 1
        for action in remote_control_cozmo.action_queue:
            action_queue_text += str(i) + ": " + remote_control_cozmo.action_to_text(action) + "<br>"
            i += 1

        return '''Action Queue:<br>''' + action_queue_text + '''
        '''
    return ""


def run(sdk_conn):
    robot = sdk_conn.wait_for_robot()
    robot.world.image_annotator.add_annotator('robotState', RobotStateDisplay)
    robot.enable_device_imu(True, True, True)

    global remote_control_cozmo
    remote_control_cozmo = RemoteControlCozmo(robot)

    # Turn on image receiving by the camera
    robot.camera.image_stream_enabled = True

    flask_helpers.run_flask(flask_app)

if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False  # RC can drive off charger if required
    try:
        cozmo.connect(run)
    except KeyboardInterrupt as e:
        pass
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
