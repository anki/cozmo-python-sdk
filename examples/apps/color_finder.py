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

'''Cozmo looks for colors.

Cozmo looks around and drives after a color if he spots it. 
See the way he processes the colors around him in the Tkviewer.

when it starts it will be waiting for
uses user inputs, explain which does what

The blinking white cube switches the Tkviewer between normal mode and pixel mode.
The other illuminated cube toggles self.color_to_find.
'''

import asyncio
import sys
import math
import functools

import cozmo

from cozmo.util import degrees, radians, abs_val, distance_mm, speed_mmps
from cozmo.lights import Color, Light
try:
    from PIL import Image, ImageDraw, ImageColor
except ImportError:
    sys.exit('Cannot import from PIL: Do `pip3 install --user Pillow` to install')


class ColorFinder(cozmo.annotate.Annotator):
    ''' one line summary of this class

        Class constants:
            color_dict (dict): map of color names to regions in color space.
                Instead of defining a color as a single (R,G,B) point,
                colors are defined with a minimum and maximum value for R, G, and B.
                For example, a point with (R,G,B) = (40,65,195) falls in the 'blue' region,
                because 0 < 40 < 70, 0 < 65 < 70, and 170 < 195 < 255.
            
            map_color_to_light (dict): associates each color name with its cozmo.lights.Light value.
                Red, green, and blue lights are already defined as constants in lights.py,
                but we need to define our own Light for yellow.

            color_distance (fn (color, color_range) => int): returns euclidean distance
                of color to color_range

        Args:
            robot (cozmo.robot.Robot): instance of the robot connected from run_program.
    '''

    color_dict = {
    'red' : (200,255,0,70,0,70),
    'green' : (0,70,170,255,0,70),
    'blue' : (0,70,0,70,170,255),
    'white' : (230,255,230,255,230,255),
    'black' : (0,30,0,30,0,30),
    'yellow' : (170,255,170,255,0,70),
    }

    map_color_to_light = {
    'green' : cozmo.lights.green_light,
    'yellow' : Light(Color(name='yellow', rgb=(255,255,0))),
    'blue' : cozmo.lights.blue_light,
    'red' : cozmo.lights.red_light
    }

    def color_distance(color,color_range):
        r,g,b = color
        minR,maxR,minG,maxG,minB,maxB = color_range
        rdist_sq = 0
        gdist_sq = 0
        bdist_sq = 0
        if r < minR:
            rdist_sq = (minR-r)**2
        if r > maxR:
            rdist_sq = (maxR-r)**2
        if g < minG:
            gdist_sq = (minG-g)**2
        if g > maxG:
            gdist_sq = (maxG-g)**2
        if b < minB:
            bdist_sq = (minB-b)**2
        if b > maxB:
            bdist_sq = (maxB-b)**2
        return rdist_sq+gdist_sq+bdist_sq

    def __init__(self,robot: cozmo.robot.Robot):

        self.robot = robot
        robot.camera.image_stream_enabled = True
        robot.camera.color_image_enabled = True
        robot.add_event_handler(cozmo.objects.EvtObjectTapped, self.on_cube_tap)
        robot.add_event_handler(cozmo.world.EvtNewCameraImage, self.on_new_camera_image)

        self.color_selector_cube = None # type: LightCube
        self.color_to_find = 'blue'
        self.possible_colors_to_find = ['green','yellow','blue','red']
        self.color_to_find_index = self.possible_colors_to_find.index(self.color_to_find)

        self.grid_cube = None # type: LightCube
        robot.world.image_annotator.add_annotator('color_finder',self)
        robot.world.image_annotator.annotation_enabled = False
        self.enabled = True
        self.grid_width = 32
        self.grid_height = 24
        self.pixel_matrix = [['white' for x in range(self.grid_height)] for y in range(self.grid_width)]

        self.amount_turned_recently = radians(0)
        self.moving_threshold = radians(6)

        self.state = 'look_around'

        self.look_around_behavior = None # type: LookAroundInPlace behavior
        self.drive_action = None # type: TurnInPlace action
        self.tilt_head_action = None # type: SetHeadAngle action
        self.rotate_action = None # type: TurnInPlace action

    def apply(self, image, scale):
    ''' Draws a grid of squares on the screen, 
        each of which is filled with the color approximated by the determine_color method.
        WM and HM are multipliers that scale the dimensions of the squares 
        based on self.grid_width and self.grid_height
    '''
        d = ImageDraw.Draw(image)
        WM = 20*32/self.grid_width
        HM = 20*24/self.grid_height

        for i in range(self.grid_width):
            for j in range(self.grid_height):
                pt1 = Point(i*WM,j*HM)
                pt2 = Point(i*WM,(j+1)*HM)
                pt3 = Point((i+1)*WM,(j+1)*HM)
                pt4 = Point((i+1)*WM,j*HM)
                points_seq=(pt1,pt2,pt3,pt4)
                cozmo.annotate.add_polygon_to_image(image,points_seq,1.0,'green',self.pixel_matrix[i][j])

        text = cozmo.annotate.ImageText('Looking for {}'.format(self.color_to_find), color='white')
        text.render(d, (0, 0, image.width, image.height))

    def on_cube_tap(self, evt, **kwargs):
    ''' The blinking white cube switches the Tkviewer between normal mode and pixel mode.
        The other illuminated cube toggles self.color_to_find.
    '''    
        if kwargs['obj'].object_id == self.color_selector_cube.object_id:
            self.toggle_color_to_find()
        elif kwargs['obj'].object_id == self.grid_cube.object_id:
            self.robot.world.image_annotator.annotation_enabled = not self.robot.world.image_annotator.annotation_enabled

    def toggle_color_to_find(self):
    ''' Sets self.color_to_find to the next color in self.possible_colors_to_find, 
        wrapping back around to the initial color if we have reached the end of the list
    '''    
        self.color_to_find_index+=1
        if self.color_to_find_index == len(self.possible_colors_to_find):
            self.color_to_find_index = 0
        self.color_to_find = self.possible_colors_to_find[self.color_to_find_index]
        self.color_selector_cube.set_lights(map_color_to_light[self.color_to_find])

    def get_low_res_view(self):
    ''' Uses the resize method from the Pillow library to get a low-resolution
        version of Cozmo's camera view.
    '''
        image = self.robot.world.latest_image.raw_image
        return image.resize((self.grid_width,self.grid_height), resample = Image.LANCZOS)

    def update_pixel_matrix(self,downsized_image):
    ''' Uses the getpixel method from the Pillow library to get the RGB values
        of all the pixels in the low-res approximation of Cozmo's camera view.
    '''
        for i in range(self.grid_width):
            for j in range(self.grid_height):
                r,g,b = downsized_image.getpixel((i,j))
                self.pixel_matrix[i][j] = self.approximate_color_of_pixel(r,g,b)
        self.fill_in_gaps_of_pixel_matrix()

    def approximate_color_of_pixel(self,r,g,b):
    '''Returns the approximate color of this pixel from color_dict.'''
        min_distance = sys.maxsize
        closest_color = ''
        for color_name, color_values in color_dict.items():
            d = color_distance((r,g,b),color_values)
            if d < min_distance:
                min_distance = d
                closest_color = color_name
        return closest_color

    def fill_in_gaps_of_pixel_matrix(self):
    '''describe this'''
        for i in range(1,self.grid_width-1):
            for j in range(1,self.grid_height-1):
                color = self.pixel_is_surrounded_by_color(i,j)
                if color:
                    self.pixel_matrix[i][j]=color

    def pixel_is_surrounded_by_color(self,i,j):
    ''' If a pixel is surrounded by three pixels of the same color, returns that color.
        Otherwise, returns None.
    '''
        if self.pixel_matrix[i-1][j]==self.pixel_matrix[i][j-1] and self.pixel_matrix[i-1][j]==self.pixel_matrix[i+1][j]:
            return self.pixel_matrix[i-1][j]
        if self.pixel_matrix[i-1][j]==self.pixel_matrix[i][j-1] and self.pixel_matrix[i-1][j]==self.pixel_matrix[i][j+1]:
            return self.pixel_matrix[i-1][j]
        if self.pixel_matrix[i-1][j]==self.pixel_matrix[i+1][j] and self.pixel_matrix[i-1][j]==self.pixel_matrix[i][j+1]:
            return self.pixel_matrix[i-1][j]
        if self.pixel_matrix[i+1][j]==self.pixel_matrix[i][j-1] and self.pixel_matrix[i+1][j]==self.pixel_matrix[i][j+1]:
            return self.pixel_matrix[i+1][j]
        return None 

    async def on_new_camera_image(self, evt, **kwargs):
    ''' Processes the blobs in Cozmo's view.
        Triggered by EvtOnNewCameraImage ~15 times a second.
    '''
        downsized_image = self.get_low_res_view()
        self.update_pixel_matrix(downsized_image)
        blob_detector = BlobDetector(self.pixel_matrix,self.possible_colors_to_find)
        blob_info = blob_detector.get_center_of_blob_with_color(self.color_to_find)
        if blob_info:
            if self.state=='look_around':
                self.state='found_color'
                self.look_around_behavior.stop()
            self.on_finding_a_blob(blob_info)
        else:
            self.robot.set_backpack_lights_off()
            self.state='look_around'

    def on_finding_a_blob(self,blob_info):
    ''' Determines whether Cozmo should continue to look at the blob, or drive towards it.
    '''    
        x,y = blob_info
        WM = 10.0*32/self.grid_width  # WM and HM are multipliers that adjust the amount to turn
        HM = 10.0*24/self.grid_height # based on the current dimensions of self.pixel_matrix.
        self.robot.set_center_backpack_lights(map_color_to_light[self.color_to_find])

        # 'fov' stands for 'field of view'. This is the angle amount
        # that Cozmo can see to the edges of his camera view.
        amount_move_head = radians(self.robot.camera.config.fov_y.radians*(120-y*HM)/240)
        amount_rotate = radians(self.robot.camera.config.fov_x.radians*(160-x*WM)/320)
        if self.moved_too_far_from_center(amount_move_head,amount_rotate):
            self.state='found_color'
        if self.state != 'driving':
            self.look_at_it(amount_move_head,amount_rotate)
        else:
            self.drive_at_it()

    def moved_too_far_from_center(self,amount_move_head,amount_rotate):
    ''' Decides whether the center of the blob is too far from the approximate center of Cozmo's view.
    '''
        too_far_vertical = abs_val(amount_move_head)>self.robot.camera.config.fov_y/8
        too_far_horizontal = abs_val(amount_rotate)>self.robot.camera.config.fov_x/8
        return (too_far_vertical or too_far_horizontal)

    def look_at_it(self,amount_move_head,amount_rotate):
    ''' Calls actions that tilt Cozmo's head and rotate his body toward the color.
    '''
        self.robot.abort_all_actions()
        new_head_angle = self.robot.head_angle + amount_move_head
        self.tilt_head_action = self.robot.set_head_angle(new_head_angle, in_parallel=True)
        self.rotate_action = self.robot.turn_in_place(amount_rotate, in_parallel=True)
        if self.state=='found_color':
            self.amount_turned_recently += abs_val(amount_move_head) + abs_val(amount_rotate)

    def drive_at_it(self):
    ''' Drives straight once prior actions have been cancelled.
    '''
        if self.tilt_head_action.is_running:
            self.tilt_head_action.abort()
        if self.rotate_action.is_running:
            self.rotate_action.abort()
        if self.drive_action == None or not self.drive_action.is_running:
            self.drive_action = self.robot.drive_straight(distance_mm(500), speed_mmps(100), should_play_anim=False, in_parallel=True)

    def turn_on_cubes(self):
    ''' Illuminates the two cubes that control self.color_to_find and set the Tkviewer display.
    '''
        self.color_selector_cube = self.robot.world.get_light_cube(cozmo.objects.LightCube1Id)
        self.color_selector_cube.set_lights(map_color_to_light[self.color_to_find])
        self.grid_cube = self.robot.world.get_light_cube(cozmo.objects.LightCube2Id)
        self.grid_cube.set_lights(cozmo.lights.white_light.flash())

    def setup(self):
        self.robot.set_head_angle(radians(0))
        self.robot.drive_straight(distance_mm(100), speed_mmps(100), should_play_anim=False, in_parallel=True)
        self.turn_on_cubes()

    async def run(self):
    ''' Updates self.state and resets self.amount_turned_recently every second.
        Program runs until typing CRTL+C into Terminal/Command Prompt,
        or by closing the Tkviewer window.
    '''    
        self.setup()
        while True:
            await asyncio.sleep(1)
            if self.state=='look_around':
                self.look_around_behavior = self.robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
            if self.state=='found_color' and self.amount_turned_recently<self.moving_threshold:
                    self.state='driving'
            self.amount_turned_recently = radians(0)

class Point:
    '''one line summary of this class

    Args:
        x (int): x value of the point. x values increase from the left of the Tkviewer to the right
        y (int): y value of the point. y values increase from the top of the Tkviewer to the bottom

    '''
    def __init__(self,x,y):
        self.x = x
        self.y = y


class BlobDetector():
    ''' Determine where the 'blobs' (regions of the same color) reside in a matrix.
        
        Args:
            matrix (int[][]) : the pixel_matrix from ColorFinder
            keylist: the list of possible_colors from ColorFinder
    '''
    def __init__(self,matrix,keylist):
        self.matrix = matrix
        self.keylist = keylist

        self.num_blobs = 1
        self.blobs_dict = {}
        self.table_of_keys = [[None for x in range(len(self.matrix[0]))] for y in range(len(self.matrix))]
        self.make_blobs_dict()
        self.filter_blobs_dict_by_size(20)

    def make_blobs_dict(self):
    ''' Construct a dictionary that maps a blob to the points of the matrix that make up that blob.
            Key : (number,color), where number is self.num_blobs at the time the blob was first created,
            and color is the color of that blob. This way we can differentiate between different blobs
            of the same color.
            Value : the list of points in the blob.
    '''
        for i in range(len(self.matrix)):
            for j in range(len(self.matrix[0])):
                if i==0:
                    if j==0:
                        self.make_upper_right_corner_blob()
                    else:
                        if self.matrix[i][j]!=self.matrix[i][j-1]:
                            self.make_new_blob_at(i,j)
                        else:
                            self.join_blob_above(i,j)
                elif j==0:
                    if self.matrix[i][j]!=self.matrix[i-1][j]:
                        self.make_new_blob_at(i,j)
                    else:
                        self.join_blob_left(i,j)
                else:
                    if self.matrix[i][j]!=self.matrix[i-1][j] and self.matrix[i][j]!=self.matrix[i][j-1]:
                        self.make_new_blob_at(i,j)
                    elif self.matrix[i][j]==self.matrix[i-1][j] and self.matrix[i][j]==self.matrix[i][j-1] and self.table_of_keys[i-1][j]!=self.table_of_keys[i][j-1]:
                        self.merge_up_and_left_blobs(i,j)
                    else:
                        if self.matrix[i][j]==self.matrix[i-1][j]:
                            self.join_blob_left(i,j)
                        else:
                            self.join_blob_above(i,j)

    def get_blobs_dict(self):
        return self.blobs_dict

    def make_upper_right_corner_blob(self):
        self.blobs_dict[(1,self.matrix[0][0])] = [(0,0)]
        self.table_of_keys[0][0] = (1,self.matrix[0][0])
        self.num_blobs+=1

    def make_new_blob_at(self,i,j):
        self.blobs_dict[(self.num_blobs,self.matrix[i][j])] = [(i,j)]
        self.table_of_keys[i][j] = (self.num_blobs,self.matrix[i][j])
        self.num_blobs+=1

    def join_blob_above(self,i,j):
        blob = self.table_of_keys[i][j-1]
        self.blobs_dict[blob].append((i,j))
        self.table_of_keys[i][j] = blob

    def join_blob_left(self,i,j):
        blob = self.table_of_keys[i-1][j]
        self.blobs_dict[blob].append((i,j))
        self.table_of_keys[i][j] = blob

    def merge_up_and_left_blobs(self,i,j):
        above_blob_key = self.table_of_keys[i][j-1]
        left_blob_key = self.table_of_keys[i-1][j]
        above_blob_points = self.blobs_dict[above_blob_key]
        left_blob_points = self.blobs_dict[left_blob_key]
        self.blobs_dict[left_blob_key] = left_blob_points + above_blob_points + [(i,j)]
        self.table_of_keys[i][j] = left_blob_key
        for (x,y) in above_blob_points:
            self.table_of_keys[x][y] = left_blob_key
        self.blobs_dict.pop(above_blob_key)

    def filter_blobs_dict_by_size(self,size):
        self.blobs_dict = dict((k, v) for k, v in self.blobs_dict.items() if len(v) >= size)

    def get_largest_blob_with_color(self,color):
        filtered_dict = dict(((n,k),v) for (n,k),v in self.blobs_dict.items() if k == color)
        values = filtered_dict.values()
        if len(values)>0:
            longest_list = functools.reduce(lambda largest, current: largest if (largest > current) else current, values)
            sample_x,sample_y = longest_list[0]
            return self.table_of_keys[sample_x][sample_y]
        else:
            return None

    def get_blob_info(self):
    ''' Give the approximate center of the blobs
        by averaging the x and y values of the points in a blob's value in blob_dict
    '''
        info = {}
        biggest_blobs = []
        for color in self.keylist:
            biggest_blobs.append(self.get_largest_blob_with_color(color))
        for blob in biggest_blobs:
            if blob:
                num,color = blob
                xs = []
                ys = []
                for (x,y) in self.blobs_dict[blob]:
                    xs.append(x)
                    ys.append(y)
                average_x = functools.reduce((lambda a,b : a+b),xs)/len(xs)
                average_y = functools.reduce((lambda a,b : a+b),ys)/len(ys)
                info[color] = (int(average_x),int(average_y))
        return info

    def get_center_of_blob_with_color(self,color):
        d = self.get_blob_info()
        if color in d:
            return d[color]
        return None


async def cozmo_program(robot: cozmo.robot.Robot):
    color_finder = ColorFinder(robot)
    await color_finder.run()

cozmo.run_program(cozmo_program, use_viewer=True, force_viewer_on_top=True)