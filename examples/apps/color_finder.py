#!/usr/bin/env python3

# Copyright (c) 2017 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Cozmo looks around and drives after colors.

Place a tennis ball near Cozmo and see if he can go play with it!

When the program starts, Cozmo will look around for the color yellow.
Tap the cube illuminated yellow to switch Cozmo's target color between yellow, blue, red, green.
Tap the blinking white cube to have the viewer display Cozmo's pixelated camera view.
'''

import asyncio
import functools
import math
import numpy
import sys

import cozmo

from cozmo.util import degrees, distance_mm, radians, speed_mmps, Vector2
from cozmo.lights import Color, Light
try:
    from PIL import Image, ImageColor, ImageDraw
except ImportError:
    sys.exit('Cannot import from PIL: Do `pip3 install --user Pillow` to install')
    
# map_color_to_light (dict): maps each color name with its cozmo.lights.Light value.
# Red, green, and blue lights are already defined as constants in lights.py, 
# but we need to define our own custom Light for yellow.
map_color_to_light = {
'green' : cozmo.lights.green_light, 
'yellow' : Light(Color(name='yellow', rgb = (255, 255, 0))), 
'blue' : cozmo.lights.blue_light, 
'red' : cozmo.lights.red_light
}

# color_ranges (dict): map of color names to regions in color space.
# Instead of defining a color as a single (R, G, B) point, 
# colors are defined with a minimum and maximum value for R, G, and B.
# For example, a point with (R, G, B) = (40, 15, 225) falls entirely in the 'blue' region, 
# because 0 < 40 < 50, 0 < 15 < 50, and 210 < 225 < 255.
# A point with (R, G, B) = (95, 240, 160) does not fall exactly in one color region.
# But applying color_distance_sqr between this color and all the colors in color_ranges
# will show that (95, 240, 160) is closest to the 'green' region.
color_ranges = {
'red' : (210, 255, 0, 50, 0, 50), 
'green' : (0, 50, 210, 255, 0, 50), 
'blue' : (0, 50, 0, 50, 210, 255), 
'white' : (195, 255, 195, 255, 195, 255), 
'black' : (0, 30, 0, 30, 0, 30),
'yellow' : (210, 255, 210, 255, 0, 70), 
}

def color_distance_sqr(color, color_range):
    '''Determines the squared euclidean distance between color and color_range.

    Args:
        color (int, int, int): the R, G, B values of the color
        color_range(int, int, int, int, int, int): the minimum and maximum for R, G, and B for the color range

    Returns:
        squared distance between color and color_range,
        which is the sum of the squared distances from 
        the R, G, B values to their respective ranges
    '''
    r, g, b = color
    minR, maxR, minG, maxG, minB, maxB = color_range
    rdist_sq = 0
    gdist_sq = 0
    bdist_sq = 0
    if r < minR:
        rdist_sq = (minR-r)**2
    elif r > maxR:
        rdist_sq = (maxR-r)**2
    if g < minG:
        gdist_sq = (minG-g)**2
    elif g > maxG:
        gdist_sq = (maxG-g)**2
    if b < minB:
        bdist_sq = (minB-b)**2
    elif b > maxB:
        bdist_sq = (maxB-b)**2
    sum_dist_sq = rdist_sq+gdist_sq+bdist_sq
    return sum_dist_sq

def color_balance(image):
    '''Adjusts the color data of an image so that the average R, G, B values across the entire image end up equal.

    This is called a 'gray-world' algorithm, because the colors
    with equal R, G, B values fall along the grayscale.
    https://web.stanford.edu/~sujason/ColorBalancing/grayworld.html

    Args:
        image (PIL image): the image being color-balanced

    Returns
        the PIL image with balanced color distribution
    '''

    image_array = from_pillow_image(image)
    image_array = image_array.transpose(2, 0, 1).astype(numpy.uint32)
    average_g = numpy.average(image_array[1])
    image_array[0] = numpy.minimum(image_array[0] * (average_g / numpy.average(image_array[0])), 255)
    image_array[2] = numpy.minimum(image_array[2] * (average_g / numpy.average(image_array[2])), 255)
    return to_pillow_image(image_array.transpose(1, 2, 0).astype(numpy.uint8))

def from_pillow_image(image):
    '''Converts PIL image to image array.'''
    image_array = numpy.asarray(image)
    image_array.flags.writeable = True
    return image_array

def to_pillow_image(image_array):
    '''Coverts image array to PIL image.'''
    return Image.fromarray(numpy.uint8(image_array))


LOOK_AROUND_STATE = 'look_around'
FOUND_COLOR_STATE = 'found_color'
DRIVING_STATE = 'driving'

ANNOTATOR_WIDTH = 640.0
ANNOTATOR_HEIGHT = 480.0


class ColorFinder(cozmo.annotate.Annotator):
    '''Cozmo looks around and drives after colors.

    Cozmo's camera view is approximated into a matrix of colors.
    Cozmo will look around for self.color_to_find, and once it is spotted, 
    he will drive in the direction of that color.

    Args:
        robot (cozmo.robot.Robot): instance of the robot connected from run_program.
    '''
    def __init__(self, robot: cozmo.robot.Robot):

        self.robot = robot
        self.robot.camera.image_stream_enabled = True
        self.robot.camera.color_image_enabled = True
        self.fov_x  = self.robot.camera.config.fov_x
        self.fov_y = self.robot.camera.config.fov_y
        self.robot.add_event_handler(cozmo.objects.EvtObjectTapped, self.on_cube_tap)
        self.robot.add_event_handler(cozmo.world.EvtNewCameraImage, self.on_new_camera_image)

        self.color_selector_cube = None # type: LightCube
        self.color_to_find = 'yellow'
        self.possible_colors_to_find = ['green', 'yellow', 'blue', 'red']
        self.color_to_find_index = self.possible_colors_to_find.index(self.color_to_find)

        self.grid_cube = None # type: LightCube
        self.robot.world.image_annotator.add_annotator('color_finder', self)
        self.robot.world.image_annotator.annotation_enabled = False
        self.enabled = True
        self.downsize_width = 32
        self.downsize_height = 24
        self.pixel_matrix = MyMatrix('white', self.downsize_width, self.downsize_height)

        self.amount_turned_recently = radians(0)
        self.moving_threshold = radians(9)

        self.state = LOOK_AROUND_STATE

        self.look_around_behavior = None # type: LookAroundInPlace behavior
        self.drive_action = None # type: DriveStraight action
        self.tilt_head_action = None # type: SetHeadAngle action
        self.rotate_action = None # type: TurnInPlace action
        self.lift_action = None # type: SetLiftHeight action

    def apply(self, image, scale):
        '''Draws a pixelated grid of Cozmo's approximate camera view onto the viewer window.
            
        WM and HM are multipliers that scale the dimensions of the annotated squares 
        based on self.downsize_width and self.downsize_height
        '''
        d = ImageDraw.Draw(image)
        WM = ANNOTATOR_WIDTH/self.downsize_width
        HM = ANNOTATOR_HEIGHT/self.downsize_height

        for i in range(self.downsize_width):
            for j in range(self.downsize_height):
                pt1 = Vector2(i*WM, j*HM)
                pt2 = Vector2(i*WM, (j+1)*HM)
                pt3 = Vector2((i+1)*WM, (j+1)*HM)
                pt4 = Vector2((i+1)*WM, j*HM)
                points_seq = (pt1, pt2, pt3, pt4)
                cozmo.annotate.add_polygon_to_image(image, points_seq, 1.0, 'green', self.pixel_matrix.at(i, j).value)

        text = cozmo.annotate.ImageText('Looking for {}'.format(self.color_to_find), color = 'white')
        text.render(d, (0, 0, image.width, image.height))

    def on_cube_tap(self, evt, obj, **kwargs):
        '''The blinking white cube switches the viewer between normal mode and pixel mode.
        The other illuminated cube toggles self.color_to_find.       
        '''    
        if obj.object_id == self.color_selector_cube.object_id:
            self.toggle_color_to_find()
        elif obj.object_id == self.grid_cube.object_id:
            self.robot.world.image_annotator.annotation_enabled = not self.robot.world.image_annotator.annotation_enabled

    def toggle_color_to_find(self):
        '''Sets self.color_to_find to the next color in self.possible_colors_to_find.'''    
        self.color_to_find_index += 1
        if self.color_to_find_index == len(self.possible_colors_to_find):
            self.color_to_find_index = 0
        self.color_to_find = self.possible_colors_to_find[self.color_to_find_index]
        self.color_selector_cube.set_lights(map_color_to_light[self.color_to_find])

    async def on_new_camera_image(self, evt, **kwargs):
        '''Processes the blobs in Cozmo's view, and determines the correct reaction.'''
        downsized_image = self.get_low_res_view()
        self.update_pixel_matrix(downsized_image)
        blob_detector = BlobDetector(self.pixel_matrix, self.possible_colors_to_find)
        blob_info = blob_detector.get_center_of_blob_with_color(self.color_to_find)
        if blob_info:
            if self.state == LOOK_AROUND_STATE:
                self.state = FOUND_COLOR_STATE
                if self.look_around_behavior:
                    self.look_around_behavior.stop()
            self.on_finding_a_blob(blob_info)
        else:
            self.robot.set_backpack_lights_off()
            self.abort_these_actions(self.drive_action)
            self.state = LOOK_AROUND_STATE

    def update_pixel_matrix(self, downsized_image):
        '''Updates self.pixel_matrix with the colors from the current camera view.

        Args:
            downsized_image (PIL image): the low-resolution version of self.robot.world.latest_image
        '''
        for i in range(self.pixel_matrix.num_cols):
            for j in range(self.pixel_matrix.num_rows):
                r, g, b = downsized_image.getpixel((i, j))
                self.pixel_matrix.at(i, j).set(self.approximate_color_of_pixel(r, g, b))
        self.pixel_matrix.fill_gaps()

    def approximate_color_of_pixel(self, r, g, b):
        '''Returns the approximated color of the RGB value of a pixel.

        Args:
            r (int): the amount of red in the pixel
            g (int): the amount of green in the pixel
            b (int): the amount of blue in the pixel

        Returns:
            string specifying the name of the color range closest to the input color
        '''
        min_distance = sys.maxsize
        closest_color = ''
        for color_name, color_values in color_ranges.items():
            d = color_distance_sqr((r, g, b), color_values)
            if d < min_distance:
                min_distance = d
                closest_color = color_name
        return closest_color

    def get_low_res_view(self):
        '''Downsizes Cozmo's camera view to the specified dimensions.

        Returns:
            PIL image downsized to low-resolution version of Cozmo's camera view.
        '''
        image = color_balance(self.robot.world.latest_image.raw_image)
        downsized_image = image.resize((self.downsize_width, self.downsize_height), resample = Image.LANCZOS)
        return downsized_image

    def on_finding_a_blob(self, blob_info):
        '''Determines whether Cozmo should continue to look at the blob, or drive towards it.
            
        Args:
            blob_info (int, int): coordinates of the blob's center in self.pixel_matrix
        '''
        self.robot.set_center_backpack_lights(map_color_to_light[self.color_to_find])
        x, y = blob_info
        # 'fov' stands for 'field of view'. This is the angle amount
        # that Cozmo can see to the edges of his camera view.
        amount_move_head = radians(self.fov_y.radians*(.5-y/self.downsize_height))
        amount_rotate = radians(self.fov_x.radians*(.5-x/self.downsize_width))
        if self.moved_too_far_from_center(amount_move_head, amount_rotate):
            self.state = FOUND_COLOR_STATE
        if self.state != DRIVING_STATE:
            self.turn_toward_color_blob(amount_move_head, amount_rotate)
        else:
            self.drive_toward_color_blob()

    def moved_too_far_from_center(self, amount_move_head, amount_rotate):
        '''Decides whether the center of the blob is too far from the center of Cozmo's view.

        Args:
            amount_move_head (cozmo.util.Angle): 
                the perceived vertical distance of the blob from center-screen
            amount_rotate (cozmo.util.Angle): 
                the perceived horizontal distance of the blob from center-screen

        Returns:
            bool specifying whether the object is too far from center-screen
        '''
        too_far_vertical = (amount_move_head.abs_val > self.fov_y/6)
        too_far_horizontal = (amount_rotate.abs_val > self.fov_x/6)
        too_far = too_far_vertical or too_far_horizontal
        return too_far

    def turn_toward_color_blob(self, amount_move_head, amount_rotate):
        '''Calls actions that tilt Cozmo's head and rotate his body toward the color.

        Args:
           amount_move_head (cozmo.util.Angle): 
               the perceived vertical distance of the blob from center-screen
           amount_rotate (cozmo.util.Angle): 
               the perceived horizontal distance of the blob from center-screen
        '''
        self.abort_these_actions(self.tilt_head_action, self.rotate_action, self.drive_action)
        new_head_angle = self.robot.head_angle + amount_move_head
        self.tilt_head_action = self.robot.set_head_angle(new_head_angle, in_parallel = True)
        self.rotate_action = self.robot.turn_in_place(amount_rotate, in_parallel = True)
        if self.state == FOUND_COLOR_STATE:
            self.amount_turned_recently += amount_move_head.abs_val + amount_rotate.abs_val

    def drive_toward_color_blob(self):
        '''Drives straight once prior actions have been cancelled.'''
        self.abort_these_actions(self.tilt_head_action, self.rotate_action)
        if self.should_start_action(self.drive_action):
            self.drive_action = self.robot.drive_straight(distance_mm(500), speed_mmps(300), should_play_anim = False, in_parallel = True)
        if self.should_start_action(self.lift_action):
            self.lift_action = self.robot.set_lift_height(1.0, in_parallel = True)

    def abort_these_actions(self, *actions):
        '''Aborts the input actions if they are currently running.

        Args:
            *actions (list): the list of actions
        '''
        for action in actions:
            if action != None and action.is_running:
                action.abort()

    def should_start_action(self, action):
        ''' Whether the action should be started.

        Args:
            action (action): the action that should or should not be started

        Returns:
            bool specifying whether the action is not running or is currently None
        '''
        should_start = ((action == None) or (not action.is_running))
        return should_start

    def turn_on_cubes(self):
        '''Illuminates the two cubes that control self.color_to_find and set the viewer display.'''
        self.color_selector_cube.set_lights(map_color_to_light[self.color_to_find])
        self.grid_cube.set_lights(cozmo.lights.white_light.flash())

    def cubes_connected(self):
        '''Returns true if Cozmo connects to both cubes successfully.'''   
        self.color_selector_cube = self.robot.world.get_light_cube(cozmo.objects.LightCube1Id)
        self.grid_cube = self.robot.world.get_light_cube(cozmo.objects.LightCube2Id)
        return not (self.color_selector_cube == None or self.grid_cube == None)

    async def run(self):
        '''Program runs until typing CRTL+C into Terminal/Command Prompt, 
        or by closing the viewer window.
        '''    
        if not self.cubes_connected():
            print("Cubes did not connect successfully - check that they are nearby. You may need to replace the batteries.")
            return
        self.turn_on_cubes()
        await self.robot.drive_straight(distance_mm(100), speed_mmps(50)).wait_for_completed()

        # Updates self.state and resets self.amount_turned_recently every 1 second.
        while True:
            await asyncio.sleep(1)
            if self.state == LOOK_AROUND_STATE:
                self.look_around_behavior = self.robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
            if self.state == FOUND_COLOR_STATE and self.amount_turned_recently < self.moving_threshold:
                self.state = DRIVING_STATE
            self.amount_turned_recently = radians(0)


class BlobDetector():
    '''Determine where the regions of the same value reside in a matrix.

    We use this class to find the areas of equal color in pixel_matrix in the ColorFinder class.
    
    Args:
        matrix (int[][]) : the pixel_matrix from ColorFinder
        keylist (list of strings): the list of possible_colors_to_find from ColorFinder
    '''
    def __init__(self, matrix, keylist):
        self.matrix = matrix
        self.keylist = keylist

        self.num_blobs = 1
        self.blobs_dict = {}
        self.keys = MyMatrix(None, self.matrix.num_cols, self.matrix.num_rows)
        self.make_blobs_dict()
        self.filter_blobs_dict_by_size(10) # prevents a lot of irrelevant blobs from being processed

    def make_blobs_dict(self):
        '''Using a connected components algorithm, constructs a dictionary 
        that maps a blob to the points of the matrix that make up that blob.

        Key and Value types of the dictionary:
            Key : (number, color), where number is self.num_blobs at the time the blob was first created, 
            and color is the color of that blob. This way, two different blobs of the same color
            have two distinct keys.
            Value : the list of points in the blob.
        '''
        for i in range(self.matrix.num_cols):
            for j in range(self.matrix.num_rows):
                matches_left = self.matches_blob_left(i, j)
                matches_above = self.matches_blob_above(i, j)
                should_merge = matches_left and matches_above and self.above_and_left_blobs_are_different(i, j)
                if should_merge:
                    self.merge_up_and_left_blobs(i, j)
                elif matches_left:
                    self.join_blob_left(i, j)
                elif matches_above:
                    self.join_blob_above(i, j)
                else:
                    self.make_new_blob_at(i, j)

    def matches_blob_above(self, i, j):
        '''Returns true if the current point matches the point above.

        Args:
            i (int): the x-coordinate in self.matrix
            j (int): the y-coordinate in self.matrix

        Returns:
            bool specifying whether the current point matches the point above.
        '''
        if j == 0:
            return False
        matches_above = (self.matrix.at(i, j).value == self.matrix.at(i, j-1).value)
        return matches_above

    def matches_blob_left(self, i, j):
        '''Returns true if the current point matches the point to the left.

        Args:
            i (int): the x-coordinate in self.matrix
            j (int): the y-coordinate in self.matrix

        Returns:
            bool specifying whether the current point matches the point to the left.
        '''
        if i == 0:
            return False
        matches_left  = (self.matrix.at(i, j).value == self.matrix.at(i-1, j).value)
        return matches_left

    def above_and_left_blobs_are_different(self, i, j):
        '''Returns true if the point above and the point to the left belong to different blobs.

        Args:
            i (int): the x-coordinate in self.matrix
            j (int): the y-coordinate in self.matrix

        Returns:
            bool specifying whether the above blob and the left blob have different keys in self.keys
        '''
        if i == 0 or j == 0:
            return False
        above_and_left_different = (self.keys.at(i-1, j).value != self.keys.at(i, j-1).value)
        return above_and_left_different

    def make_new_blob_at(self, i, j):
        '''Adds a new blob to self.blob_dict 
        whose list of points initially contains only the current point.

        Args:
            i (int): the x-coordinate in self.matrix
            j (int): the y-coordinate in self.matrix
        '''
        self.blobs_dict[(self.num_blobs, self.matrix.at(i, j).value)] = [(i, j)]
        self.keys.at(i, j).set((self.num_blobs, self.matrix.at(i, j).value))
        self.num_blobs += 1

    def join_blob_above(self, i, j):
        '''Adds current point to the blob above.

        Args:
            i (int): the x-coordinate in self.matrix
            j (int): the y-coordinate in self.matrix
        '''
        above_blob_key = self.keys.at(i, j-1).value
        self.blobs_dict[above_blob_key].append((i, j))
        self.keys.at(i, j).set(above_blob_key)

    def join_blob_left(self, i, j):
        '''Adds current point to the blob to the left.

        Args:
            i (int): the x-coordinate in self.matrix
            j (int): the y-coordinate in self.matrix
        '''
        left_blob_key = self.keys.at(i-1, j).value
        self.blobs_dict[left_blob_key].append((i, j))
        self.keys.at(i, j).set(left_blob_key)

    def merge_up_and_left_blobs(self, i, j):
        '''Adds current point and points from the above blob into left blob, 
        then removes the above blob from self.blob_dict

        Args:
            i (int): the x-coordinate in self.matrix
            j (int): the y-coordinate in self.matrix
        '''
        above_blob_key = self.keys.at(i, j-1).value
        left_blob_key = self.keys.at(i-1, j).value
        above_blob_points = self.blobs_dict[above_blob_key]
        left_blob_points = self.blobs_dict[left_blob_key]
        for point in above_blob_points:
            self.blobs_dict[left_blob_key].append(point)
        self.blobs_dict[left_blob_key].append((i, j))
        self.keys.at(i, j).set(left_blob_key)
        for (x, y) in above_blob_points:
            self.keys.at(x, y).set(left_blob_key)
        self.blobs_dict.pop(above_blob_key)

    def filter_blobs_dict_by_size(self, n):
        '''Filters out small blobs from self.blobs_dict.

        Args:
            n (int): the number of points required of a blob to stay in self.blobs_dict
        '''
        self.blobs_dict = dict((blob, list_of_points) for blob, list_of_points in self.blobs_dict.items() if len(list_of_points) >= n)

    def get_largest_blob_with_color(self, color):
        '''Finds the largest blob of a particular color

        Args:
            color (string): the desired color of the blob

        Returns:
            (int, string) specifying the key of the largest blob with that color, or None if no such blob exists
        '''
        filtered_dict = dict(((n, k), v) for (n, k), v in self.blobs_dict.items() if k == color)
        values = filtered_dict.values()
        if len(values) > 0:
            longest_blob_list = functools.reduce(lambda largest, current: largest if (largest > current) else current, values)
            sample_x, sample_y = longest_blob_list[0]
            return self.keys.at(sample_x, sample_y).value
        else:
            return None

    def make_blob_centers(self):
        '''Constructs a dictionary to keep track of the center of each blob.

        Returns:
            dict of blob centers
                Key: color (string): the color of the blob
                Value: x, y (int, int): the approximate center of the blob as coordinates of self.matrix
        '''
        info = {}
        biggest_blobs = []
        for color in self.keylist:
            biggest_blobs.append(self.get_largest_blob_with_color(color))
        for blob in biggest_blobs:
            if blob:
                num, color = blob
                xs = []
                ys = []
                for (x, y) in self.blobs_dict[blob]:
                    xs.append(x)
                    ys.append(y)
                average_x = functools.reduce((lambda a, b : a+b), xs)/len(xs)
                average_y = functools.reduce((lambda a, b : a+b), ys)/len(ys)
                info[color] = (int(average_x), int(average_y))
        return info

    def get_center_of_blob_with_color(self, color):
        '''Gets the center of a blob if there is a blob with the specified color. Otherwise, returns None.

        Args:
            color (string): the desired color of a blob

        Returns:
            (int, int) specifying the coordinates of the center of the desired blob, 
            or None if there is no blob of that color
        '''
        d = self.make_blob_centers()
        if color in d:
            return d[color]
        return None


class MyMatrix():
    '''A custom class to get dimensions, values, and neighboring values of the pixel_matrix.

    Args:
        initial_value : the value assigned to every MatrixValueContainer when building the matrix
        num_cols (int): the number of columns in the matrix, specified in ColorFinder as downsize_width
        num_rows (int): the number of rows in the matrix, specified in ColorFinder as downsize_height
    '''
    def __init__(self, initial_value, num_cols, num_rows):
        self.num_cols = num_cols
        self.num_rows = num_rows
        self._matrix = [[MatrixValueContainer(initial_value) for _ in range(self.num_rows)] for _ in range(self.num_cols)]

    def at(self, i, j):
        '''Gets the desired MatrixValueContainer object.

        Args:
            i (int): the x-coordinate in self
            j (int): the y-coordinate in self

        Returns:
            the MatrixValueContainer at the specified coordinates
        '''
        return self._matrix[i][j]

    def fill_gaps(self):
        '''Fills in squares in self._matrix that meet the condition in the surrounded method.
        '''
        for i in range(self.num_cols):
            for j in range(self.num_rows):
                val = self.surrounded(i,j)
                if val:
                    self.at(i, j).set(val)

    def surrounded(self, i, j):
        '''Checks if a point is surrounded by at least 3 points of the same value.

        Args:
            i (int): the x-coordinate in self._matrix
            j (int): the y-coordinate in self._matrix

        Returns:
            the surrounding value if the condition is True, otherwise returns None
            When used in the context of ColorFinder, the surrounding value would be the string
            specifying the name of the color surrounding this square.
        '''
        if i != 0 and i != self.num_cols-1 and j != 0 and j != self.num_rows-1:
            left_value, up_value, right_value, down_value = self.get_neighboring_values(i, j)
            if left_value == up_value and left_value == right_value:
                return left_value
            if left_value == up_value and left_value == down_value:
                return left_value
            if left_value == right_value and left_value == down_value:
                return left_value
            if right_value == up_value and right_value == down_value:
                return right_value
        return None

    def get_neighboring_values(self, i, j):
        '''Returns the values in the four surrounding MatrixValueContainers.
        
        Args:
            i (int): the x-coordinate in self._matrix
            j (int): the y-coordinate in self._matrix

        Returns:
            A four-tuple containing (left_value, up_value, right_value, and down_value)
        '''
        return (self.at(i-1, j), self.at(i, j-1), self.at(i+1, j), self.at(i, j+1))


class MatrixValueContainer():
    '''Simple container for values in a MyMatrix object.

    This class is intended to clean the syntax of setting
    a new value in the MyMatrix object.

    So we replace this:
        matrix.get_value(i, j)
        matrix.set_value(i, j, new_value)
    with this:
        matrix.at(i, j).value
        matrix.at(i, j).set(new_value)

    Args:
        value : the value of the MatrixValue
    '''
    def __init__(self, value):
        self.value = value

    def set(self, new_value):
        self.value = new_value


async def cozmo_program(robot: cozmo.robot.Robot):
    color_finder = ColorFinder(robot)
    await color_finder.run()

cozmo.robot.Robot.drive_off_charger_on_connect = True
cozmo.run_program(cozmo_program, use_viewer = True, force_viewer_on_top = True)
