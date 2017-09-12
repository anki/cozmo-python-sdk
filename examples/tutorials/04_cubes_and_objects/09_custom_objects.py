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

'''This example demonstrates how you can define custom objects.

The example defines several custom objects (2 cubes, a wall and a box). When
Cozmo sees the markers for those objects he will report that he observed an
object of that size and shape there.

You can adjust the markers, marker sizes, and object sizes to fit whatever
object you have and the exact size of the markers that you print out.
'''

import time

import cozmo
from cozmo.objects import CustomObject, CustomObjectMarkers, CustomObjectTypes


def handle_object_appeared(evt, **kw):
    # This will be called whenever an EvtObjectAppeared is dispatched -
    # whenever an Object comes into view.
    if isinstance(evt.obj, CustomObject):
        print("Cozmo started seeing a %s" % str(evt.obj.object_type))


def handle_object_disappeared(evt, **kw):
    # This will be called whenever an EvtObjectDisappeared is dispatched -
    # whenever an Object goes out of view.
    if isinstance(evt.obj, CustomObject):
        print("Cozmo stopped seeing a %s" % str(evt.obj.object_type))


def custom_objects(robot: cozmo.robot.Robot):
    # Add event handlers for whenever Cozmo sees a new object
    robot.add_event_handler(cozmo.objects.EvtObjectAppeared, handle_object_appeared)
    robot.add_event_handler(cozmo.objects.EvtObjectDisappeared, handle_object_disappeared)

    # define a unique cube (44mm x 44mm x 44mm) (approximately the same size as a light cube)
    # with a 30mm x 30mm Diamonds2 image on every face
    cube_obj = robot.world.define_custom_cube(CustomObjectTypes.CustomType00,
                                              CustomObjectMarkers.Diamonds2,
                                              44,
                                              30, 30, True)

    # define a unique cube (88mm x 88mm x 88mm) (approximately 2x the size of a light cube)
    # with a 50mm x 50mm Diamonds3 image on every face
    big_cube_obj = robot.world.define_custom_cube(CustomObjectTypes.CustomType01,
                                              CustomObjectMarkers.Diamonds3,
                                              88,
                                              50, 50, True)

    # define a unique wall (150mm x 120mm (x10mm thick for all walls)
    # with a 50mm x 30mm Circles2 image on front and back
    wall_obj = robot.world.define_custom_wall(CustomObjectTypes.CustomType02,
                                              CustomObjectMarkers.Circles2,
                                              150, 120,
                                              50, 30, True)

    # define a unique box (60mm deep x 140mm width x100mm tall)
    # with a different 30mm x 50mm image on each of the 6 faces
    box_obj = robot.world.define_custom_box(CustomObjectTypes.CustomType03,
                                            CustomObjectMarkers.Hexagons2,  # front
                                            CustomObjectMarkers.Circles3,   # back
                                            CustomObjectMarkers.Circles4,   # top
                                            CustomObjectMarkers.Circles5,   # bottom
                                            CustomObjectMarkers.Triangles2, # left
                                            CustomObjectMarkers.Triangles3, # right
                                            60, 140, 100,
                                            30, 50, True)

    if ((cube_obj is not None) and (big_cube_obj is not None) and
            (wall_obj is not None) and (box_obj is not None)):
        print("All objects defined successfully!")
    else:
        print("One or more object definitions failed!")
        return

    print("Show the above markers to Cozmo and you will see the related objects "
          "annotated in Cozmo's view window, you will also see print messages "
          "everytime a custom object enters or exits Cozmo's view.")

    print("Press CTRL-C to quit")
    while True:
        time.sleep(0.1)


cozmo.run_program(custom_objects, use_3d_viewer=True, use_viewer=True)
