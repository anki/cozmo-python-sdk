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

'''This module provides a 3D visualizer for Cozmo's world state.

It uses PyOpenGL, a Python OpenGL 3D graphics library which is available on most
platforms. It also depends on the Pillow library for image processing.

The easiest way to make use of this viewer is to call :func:`cozmo.run_program`
with `use_3d_viewer=True` or :func:`cozmo.run.connect_with_3dviewer`.

Warning:
    This package requires Python to have the PyOpenGL package installed, along
    with an implementation of GLUT (OpenGL Utility Toolkit).

    To install the Python packages do ``pip3 install --user "cozmo[3dviewer]"``

    On Windows and Linux you must also install freeglut (macOS / OSX has one
    preinstalled).

    On Linux: ``sudo apt-get install freeglut3``

    On Windows: Go to http://freeglut.sourceforge.net/ to get a ``freeglut.dll``
    file. It's included in any of the `Windows binaries` downloads. Place the DLL
    next to your Python script, or install it somewhere in your PATH to allow any
    script to use it."
'''


# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['DynamicTexture', 'LoadedObjFile', 'OpenGLViewer', 'OpenGLWindow',
           'RenderableObject',
           'LoadMtlFile']


import collections
import math
import time
from pkg_resources import resource_stream

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from PIL import Image

from .exceptions import InvalidOpenGLGlutImplementation, RobotBusy
from . import logger
from . import nav_memory_map
from . import objects
from . import robot
from . import util
from . import world


# Check if OpenGL imported correctly and bound to a valid GLUT implementation


def _glut_install_instructions():
    if sys.platform.startswith('linux'):
        return "Install freeglut: `sudo apt-get install freeglut3`"
    elif sys.platform.startswith('darwin'):
        return "GLUT should already be installed by default on macOS!"
    elif sys.platform in ('win32', 'cygwin'):
        return "Install freeglut: You can download it from http://freeglut.sourceforge.net/ \n"\
            "You just need the `freeglut.dll` file, from any of the 'Windows binaries' downloads. "\
            "Place the DLL next to your Python script, or install it somewhere in your PATH "\
            "to allow any script to use it."
    else:
        return "(Instructions unknown for platform %s)" % sys.platform


def _verify_glut_init():
    # According to the documentation, just checking bool(glutInit) is supposed to be enough
    # However on Windows with no GLUT DLL that can still pass, even if calling the method throws a null function error.
    if bool(glutInit):
        try:
            glutInit()
            return True
        except OpenGL.error.NullFunctionError as e:
            pass

    return False


if not _verify_glut_init():
    raise InvalidOpenGLGlutImplementation(_glut_install_instructions())


_resource_package = __name__  # All resources are in subdirectories from this file's location


# Global viewer instance
opengl_viewer = None  # type: OpenGLViewer


class DynamicTexture:
    """Wrapper around An OpenGL Texture that can be dynamically updated."""

    def __init__(self):
        self._texId =  glGenTextures(1)
        self._width = None
        self._height = None
        # Bind an ID for this texture
        glBindTexture(GL_TEXTURE_2D, self._texId)
        # Use bilinear filtering if the texture has to be scaled
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def bind(self):
        """Bind the texture for rendering."""
        glBindTexture(GL_TEXTURE_2D, self._texId)

    def update(self, pil_image: Image.Image):
        """Update the texture to contain the provided image.

        Args:
            pil_image (PIL.Image.Image): The image to write into the texture.
        """
        # Ensure the image is in RGBA format and convert to the raw RGBA bytes.
        image_width, image_height = pil_image.size
        image = pil_image.convert("RGBA").tobytes("raw", "RGBA")

        # Bind the texture so that it can be modified.
        self.bind()
        if (self._width==image_width) and (self._height==image_height):
            # Same size - just need to update the texels.
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, image_width, image_height,
                            GL_RGBA, GL_UNSIGNED_BYTE, image)
        else:
            # Different size than the last frame (e.g. the Window is resizing)
            # Create a new texture of the correct size.
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height,
                         0, GL_RGBA, GL_UNSIGNED_BYTE, image)

        self._width = image_width
        self._height = image_height


def LoadMtlFile(filename):
    """Load a .mtl material file, and return the contents as a dictionary.

    Supports the subset of MTL required for the Cozmo 3D viewer assets.

    Args:
        filename (str): The filename of the file to load.

    Returns:
        dict: A dictionary mapping named MTL attributes to values.
    """
    contents = {}
    current_mtl = None

    resource_path = '/'.join(('assets', filename))  # Note: Deliberately not os.path.join, for use with pkg_resources
    file_data = resource_stream(_resource_package, resource_path)

    for line in file_data:
        line = line.decode("utf-8")  # Convert bytes line to a string
        if line.startswith('#'):
            # ignore comments in the file
            continue
        values = line.split()
        if not values:
            # ignore empty lines
            continue
        attribute_name = values[0]
        if attribute_name == 'newmtl':
            # Create a new empty material
            current_mtl = contents[values[1]] = {}
        elif current_mtl is None:
            raise ValueError("mtl file must start with newmtl statement")
        elif attribute_name == 'map_Kd':
            # Diffuse texture map - load the image into memory
            image_name = values[1]
            image_resource_path = '/'.join(('assets', image_name))  # Note: Deliberately not os.path.join, for use with pkg_resources
            image_file_data = resource_stream(_resource_package, image_resource_path)
            with Image.open(image_file_data) as image:
                image_width, image_height = image.size
                image = image.convert("RGBA").tobytes("raw", "RGBA")

            # Bind the image as a texture that can be used for rendering
            texture_id =  glGenTextures(1)
            current_mtl['texture_Kd'] = texture_id

            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height,
                         0, GL_RGBA, GL_UNSIGNED_BYTE, image)
        else:
            # Store the values for this attribute as a list of float values
            current_mtl[attribute_name] = list(map(float, values[1:]))
    # File loaded successfully - return the contents
    return contents


class LoadedObjFile:
    """The loaded / parsed contents of a 3D Wavefront OBJ file.

    This is the intermediary step between the file on the disk, and a renderable
    3D object. It supports the subset of the OBJ file that was used in the
    Cozmo and Cube assets, and does not attempt to exhaustively support every
    possible setting.

    Args:
        filename (str): The filename of the OBJ file to load.
    """
    def __init__(self, filename):
        # list: The vertices (each vertex stored as list of 3 floats).
        self.vertices = []
        # list: The vertex normals (each normal stored as list of 3 floats).
        self.normals = []
        # list: The texture coordinates (each coordinate stored as list of 2 floats).
        self.tex_coords = []
        # dict: The faces for each mesh, indexed by mesh name.
        self.mesh_faces = {}

        # dict: A dictionary mapping named MTL attributes to values.
        self.mtl = None

        group_name = None
        material = None

        resource_path = '/'.join(('assets', filename))  # Note: Deliberately not os.path.join, for use with pkg_resources
        file_data = resource_stream(_resource_package, resource_path)

        for line in file_data:
            line = line.decode("utf-8")  # Convert bytes to string
            if line.startswith('#'):
                # ignore comments in the file
                continue

            values = line.split()
            if not values:
                # ignore empty lines
                continue

            if values[0] == 'v':
                # vertex position
                v = list(map(float, values[1:4]))
                self.vertices.append(v)
            elif values[0] == 'vn':
                # vertex normal
                v = list(map(float, values[1:4]))
                self.normals.append(v)
            elif values[0] == 'vt':
                # texture coordinate
                self.tex_coords.append(list(map(float, values[1:3])))
            elif values[0] in ('usemtl', 'usemat'):
                # material
                material = values[1]
            elif values[0] == 'mtllib':
                # material library (a filename)
                self.mtl = LoadMtlFile(values[1])
            elif values[0] == 'f':
                # A face made up of 3 or 4 vertices - e.g. `f v1 v2 v3` or `f v1 v2 v3 v4`
                # where each vertex definition is multiple indexes seperated by
                # slashes and can follow the following formats:
                # position_index
                # position_index/tex_coord_index
                # position_index/tex_coord_index/normal_index
                # position_index//normal_index

                positions = []
                tex_coords = []
                normals = []

                for vertex in values[1:]:
                    vertex_components = vertex.split('/')

                    positions.append(int(vertex_components[0]))

                    # There's only a texture coordinate if there's at least 2 entries and the 2nd entry is non-zero length
                    if len(vertex_components) >= 2 and len(vertex_components[1]) > 0:
                        tex_coords.append(int(vertex_components[1]))
                    else:
                        # OBJ file indexing starts at 1, so use 0 to indicate no entry
                        tex_coords.append(0)

                    # There's only a normal if there's at least 2 entries and the 2nd entry is non-zero length
                    if len(vertex_components) >= 3 and len(vertex_components[2]) > 0:
                        normals.append(int(vertex_components[2]))
                    else:
                        # OBJ file indexing starts at 1, so use 0 to indicate no entry
                        normals.append(0)

                try:
                    mesh_face = self.mesh_faces[group_name]
                except KeyError:
                    # Create a new mesh group
                    self.mesh_faces[group_name] = []
                    mesh_face = self.mesh_faces[group_name]

                mesh_face.append((positions, normals, tex_coords, material))
            elif values[0] == 'o':
                # object name - ignore
                pass
            elif values[0] == 'g':
                # group name (for a sub-mesh)
                group_name = values[1]
            elif values[0] == 's':
                # smooth shading (1..20, and 'off') - ignore
                pass
            else:
                logger.warning("LoadedObjFile Ignoring unhandled type '%s' in line %s",
                               values[0], values)


class RenderableObject:
    """Container for an object that can be rendered via OpenGL.

    Can contain multiple meshes, for e.g. articulated objects.

    Args:
        object_data (LoadedObjFile): The object data (vertices, faces, etc.)
            to generate the renderable object from.
        override_mtl (dict): An optional material to use as an override instead
            of the material specified in the data. This allows one OBJ file
            to be used to create multiple objects with different materials
            and textures. Use :meth:`LoadMtlFile` to generate a dict from a
            MTL file.
    """
    def __init__(self, object_data: LoadedObjFile, override_mtl=None):
        #: dict: The individual meshes, indexed by name, for this object.
        self.meshes = {}
        mtl_dict = override_mtl if (override_mtl is not None) else object_data.mtl

        def _as_rgba(color):
            if len(color) >= 4:
                return color
            else:
                # RGB - add alpha defaulted to 1
                return color + [1.0]

        for key in object_data.mesh_faces:
            new_gl_list = glGenLists(1)
            glNewList(new_gl_list, GL_COMPILE)

            self.meshes[key] = new_gl_list

            part_faces = object_data.mesh_faces[key]

            glEnable(GL_TEXTURE_2D)
            glFrontFace(GL_CCW)

            for face in part_faces:
                vertices, normals, texture_coords, material = face

                mtl = mtl_dict[material]
                if 'texture_Kd' in mtl:
                    # use diffuse texture map
                    glBindTexture(GL_TEXTURE_2D, mtl['texture_Kd'])
                else:
                    # No texture map
                    glBindTexture(GL_TEXTURE_2D, 0)

                # Diffuse light
                mtl_kd_rgba = _as_rgba(mtl['Kd'])
                glColor(mtl_kd_rgba)

                # Ambient light
                if 'Ka' in mtl:
                    mtl_ka_rgba = _as_rgba(mtl['Ka'])
                    glMaterialfv(GL_FRONT, GL_AMBIENT, mtl_ka_rgba)
                    glMaterialfv(GL_FRONT, GL_DIFFUSE, mtl_kd_rgba)
                else:
                    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, mtl_kd_rgba);

                # Specular light
                if 'Ks' in mtl:
                    mtl_ks_rgba = _as_rgba(mtl['Ks'])
                    glMaterialfv(GL_FRONT, GL_SPECULAR, mtl_ks_rgba);
                    if 'Ns' in mtl:
                        specular_exponent = mtl['Ns']
                        glMaterialfv(GL_FRONT, GL_SHININESS, specular_exponent);

                # Polygon (N verts) with optional normals and tex coords
                glBegin(GL_POLYGON)
                for i in range(len(vertices)):
                    normal_index = normals[i]
                    if normal_index > 0:
                        glNormal3fv(object_data.normals[normal_index - 1])
                    tex_coord_index = texture_coords[i]
                    if tex_coord_index > 0:
                        glTexCoord2fv( object_data.tex_coords[tex_coord_index - 1])
                    glVertex3fv(object_data.vertices[vertices[i] - 1])
                glEnd()

            glDisable(GL_TEXTURE_2D)
            glEndList()

    def draw_all(self):
        """Draw all of the meshes."""
        for mesh in self.meshes.values():
            glCallList(mesh)


def _make_unit_cube():
    """Make a unit-size cube, with normals, centered at the origin"""
    new_gl_list = glGenLists(1)
    glNewList(new_gl_list, GL_COMPILE)

    # build each of the 6 faces
    for face_index in range(6):
        # calculate normal and vertices for this face
        vertex_normal = [0.0, 0.0, 0.0]
        vertex_pos_options1 = [-1.0, 1.0,  1.0, -1.0]
        vertex_pos_options2 = [ 1.0, 1.0, -1.0, -1.0]
        face_index_even = ((face_index % 2) == 0)
        # odd and even faces point in opposite directions
        normal_dir = 1.0 if face_index_even else -1.0
        if face_index < 2:
            # -X and +X faces (vert positions differ in Y,Z)
            vertex_normal[0] = normal_dir
            v1i = 1
            v2i = 2
        elif face_index < 4:
            # -Y and +Y faces (vert positions differ in X,Z)
            vertex_normal[1] = normal_dir
            v1i = 0
            v2i = 2
        else:
            # -Z and +Z faces (vert positions differ in X,Y)
            vertex_normal[2] = normal_dir
            v1i = 0
            v2i = 1

        vertex_pos = list(vertex_normal)

        # Polygon (N verts) with optional normals and tex coords
        glBegin(GL_POLYGON)
        for vert_index in range(4):
            vertex_pos[v1i] = vertex_pos_options1[vert_index]
            vertex_pos[v2i] = vertex_pos_options2[vert_index]
            glNormal3fv(vertex_normal)
            glVertex3fv(vertex_pos)
        glEnd()

    glEndList()

    return new_gl_list


class OpenGLWindow():
    """A Window displaying an OpenGL viewport.

    Args:
        x (int): The initial x coordinate of the window in pixels.
        y (int): The initial y coordinate of the window in pixels.
        width (int): The initial height of the window in pixels.
        height (int): The initial height of the window in pixels.
        window_name (str): The name / title for the window.
        is_3d (bool): True to create a Window for 3D rendering.
    """
    def __init__(self, x, y, width, height, window_name, is_3d):
        self._pos = (x, y)
        #: int: The width of the window
        self.width = width
        #: int: The height of the window
        self.height = height
        self._gl_window = None
        self._window_name = window_name
        self._is_3d = is_3d

    def init_display(self):
        """Initialze the OpenGL display parts of the Window.

        Warning:
            Must be called on the same thread as OpenGL (usually the main thread),
            and after glutInit().
        """
        glutInitWindowSize(self.width, self.height)
        glutInitWindowPosition(*self._pos)
        self.gl_window = glutCreateWindow(self._window_name)

        if self._is_3d:
            glClearColor(0, 0, 0, 0)
            glEnable(GL_DEPTH_TEST)
            glShadeModel(GL_SMOOTH)

        glutReshapeFunc(self._reshape)

    def _reshape(self, width, height):
        # Called from OpenGL whenever this window is resized.
        self.width = width
        self.height = height
        glViewport(0, 0, width, height)


class RobotRenderFrame():
    """Minimal copy of a Robot's state for 1 frame of rendering."""
    def __init__(self, robot):
        self.pose = robot.pose
        self.head_angle = robot.head_angle
        self.lift_position = robot.lift_position


class ObservableElementRenderFrame():
    """Minimal copy of a Cube's state for 1 frame of rendering."""
    def __init__(self, element):
        self.pose = element.pose
        self.is_visible = element.is_visible
        self.last_observed_time = element.last_observed_time

    @property
    def time_since_last_seen(self):
        # Equivalent of ObservableElement's method
        '''float: time since this element was last seen (math.inf if never)'''
        if self.last_observed_time is None:
            return math.inf
        return time.time() - self.last_observed_time


class CubeRenderFrame(ObservableElementRenderFrame):
    """Minimal copy of a Cube's state for 1 frame of rendering."""
    def __init__(self, cube):
        super().__init__(cube)


class FaceRenderFrame(ObservableElementRenderFrame):
    """Minimal copy of a Face's state for 1 frame of rendering."""
    def __init__(self, face):
        super().__init__(face)


class CustomObjectRenderFrame(ObservableElementRenderFrame):
    """Minimal copy of a CustomObject's state for 1 frame of rendering."""
    def __init__(self, obj, is_fixed):
        if is_fixed:
            # Not an observable, so init directly
            self.pose = obj.pose
            self.is_visible = None
            self.last_observed_time = None
        else:
            super().__init__(obj)

        self.is_fixed = is_fixed
        self.x_size_mm = obj.x_size_mm
        self.y_size_mm = obj.y_size_mm
        self.z_size_mm = obj.z_size_mm


class WorldRenderFrame():
    """Minimal copy of the World's state for 1 frame of rendering."""
    def __init__(self, robot):
        world = robot.world

        self.robot_frame = RobotRenderFrame(robot)

        self.cube_frames = []
        for i in range(3):
            cube_id = objects.LightCubeIDs[i]
            cube = world.get_light_cube(cube_id)
            if cube is None:
                self.cube_frames.append(None)
            else:
                self.cube_frames.append(CubeRenderFrame(cube))

        self.face_frames = []
        for face in world._faces.values():
            # Ignore faces that have a newer version (with updated id)
            # or if they haven't been seen in a while).
            if not face.has_updated_face_id and (face.time_since_last_seen < 60):
                self.face_frames.append(FaceRenderFrame(face))

        self.custom_object_frames = []
        for obj in world._objects.values():
            is_custom = isinstance(obj, objects.CustomObject)
            is_fixed = isinstance(obj, objects.FixedCustomObject)
            if is_custom or is_fixed:
                self.custom_object_frames.append(CustomObjectRenderFrame(obj, is_fixed))


class RobotControlIntents():
    """Input intents for controlling the robot.

    These are sent from the OpenGL thread, and consumed by the SDK thread for
    issuing movement commands on Cozmo (to provide a remote-control interface).
    """
    def __init__(self, left_wheel_speed=0.0, right_wheel_speed=0.0,
                 lift_speed=0.0, head_speed=0.0):
        self.left_wheel_speed = left_wheel_speed
        self.right_wheel_speed = right_wheel_speed
        self.lift_speed = lift_speed
        self.head_speed = head_speed


class OpenGLViewer():
    """OpenGL based 3D Viewer.

    Handles rendering of both a 3D world view and a 2D camera window.

    Args:
        enable_camera_view (bool): True to also open a 2nd window to display
            the live camera view.
        show_viewer_controls (bool): Specifies whether to draw controls on the view.
    """
    def __init__(self, enable_camera_view, show_viewer_controls=True):
        # Queues from SDK thread to OpenGL thread
        self._img_queue = collections.deque(maxlen=1)
        self._nav_memory_map_queue = collections.deque(maxlen=1)
        self._world_frame_queue = collections.deque(maxlen=1)
        # Queue from OpenGL thread to SDK thread
        self._input_intent_queue = collections.deque(maxlen=1)

        self._last_robot_control_intents = RobotControlIntents()

        self._is_keyboard_control_enabled = False

        self._image_handler = None
        self._nav_map_handler = None
        self._robot_state_handler = None
        self._exit_requested = False

        global opengl_viewer
        if opengl_viewer is not None:
            logger.error("Multiple OpenGLViewer instances not expected: "
                         "OpenGL / GLUT only supports running 1 blocking instance on the main thread.")
        opengl_viewer = self

        self.main_window = OpenGLWindow(0, 0, 800, 600,
                                        b"Cozmo 3D Visualizer", is_3d=True)

        self._camera_view_texture = None  # type: DynamicTexture
        self.viewer_window = None  # type: OpenGLWindow
        if enable_camera_view:
            self.viewer_window = OpenGLWindow(self.main_window.width, 0, 640, 480,
                                              b"Cozmo CameraFeed", is_3d=False)

        self.cozmo_object = None  # type: RenderableObject
        self.cube_objects = []

        self._latest_world_frame = None  # type: WorldRenderFrame
        self._nav_memory_map_display_list = None

        # Keyboard
        self._is_key_pressed = {}
        self._is_alt_down = False
        self._is_ctrl_down = False
        self._is_shift_down = False

        # Mouse
        self._is_mouse_down = {}
        self._mouse_pos = None  # type: util.Vector2

        # Controls
        self._show_controls = show_viewer_controls
        self._instructions = '\n'.join(['W, S: Move forward, backward',
                                        'A, D: Turn left, right',
                                        'R, F: Lift up, down',
                                        'T, G: Head up, down',
                                        '',
                                        'LMB: Rotate camera',
                                        'RMB: Move camera',
                                        'LMB + RMB: Move camera up/down',
                                        'LMB + Z: Zoom camera',
                                        'X: same as RMB',
                                        'TAB: center view on robot',
                                        '',
                                        'H: Toggle help'])

        # Camera position and orientation defined by a look-at positions
        # and a pitch/and yaw to rotate around that along with a distance
        self._camera_look_at = util.Vector3(100.0, -25.0, 0.0)
        self._camera_pitch = math.radians(40)
        self._camera_yaw = math.radians(270)
        self._camera_distance = 500.0
        self._camera_pos = util.Vector3(0, 0, 0)
        self._camera_up = util.Vector3(0.0, 0.0, 1.0)
        self._calculate_camera_pos()

    def _request_exit(self):
        self._exit_requested = True
        if bool(glutLeaveMainLoop):
            glutLeaveMainLoop()

    def _calculate_camera_pos(self):
        # Calculate camera position based on look-at, distance and angles
        cos_pitch = math.cos(self._camera_pitch)
        sin_pitch = math.sin(self._camera_pitch)
        cos_yaw = math.cos(self._camera_yaw)
        sin_yaw = math.sin(self._camera_yaw)
        cam_distance = self._camera_distance
        cam_look_at = self._camera_look_at

        self._camera_pos._x = cam_look_at.x + (cam_distance * cos_pitch * cos_yaw)
        self._camera_pos._y = cam_look_at.y + (cam_distance * cos_pitch * sin_yaw)
        self._camera_pos._z = cam_look_at.z + (cam_distance * sin_pitch)

    def _update_modifier_keys(self):
        modifiers = glutGetModifiers()
        self._is_alt_down = (modifiers & GLUT_ACTIVE_ALT != 0)
        self._is_ctrl_down = (modifiers & GLUT_ACTIVE_CTRL != 0)
        self._is_shift_down = (modifiers & GLUT_ACTIVE_SHIFT != 0)

    def _update_intents_for_robot(self):
        # Update driving intents based on current input, and pass to SDK thread
        # so that it can pass the input on to the robot.
        def get_intent_direction(key1, key2):
            # Helper for keyboard inputs that have 1 positive and 1 negative input
            pos_key = self._is_key_pressed.get(key1, False)
            neg_key = self._is_key_pressed.get(key2, False)
            return pos_key - neg_key

        drive_dir = get_intent_direction(b'w', b's')
        turn_dir = get_intent_direction(b'd', b'a')
        lift_dir = get_intent_direction(b'r', b'f')
        head_dir = get_intent_direction(b't', b'g')

        if drive_dir < 0:
            # It feels more natural to turn the opposite way when reversing
            turn_dir = -turn_dir

        # Scale drive speeds with SHIFT (faster) and ALT (slower)
        if self._is_shift_down:
            speed_scalar = 2.0
        elif self._is_alt_down:
            speed_scalar = 0.5
        else:
            speed_scalar = 1.0

        drive_speed = 75.0 * speed_scalar
        turn_speed = 100.0 * speed_scalar

        left_wheel_speed = (drive_dir * drive_speed) + (turn_speed * turn_dir)
        right_wheel_speed = (drive_dir * drive_speed) - (turn_speed * turn_dir)
        lift_speed = 4.0 * lift_dir * speed_scalar
        head_speed = head_dir * speed_scalar

        control_intents = RobotControlIntents(left_wheel_speed, right_wheel_speed,
                                              lift_speed, head_speed)
        self._input_intent_queue.append(control_intents)

    def _idle(self):
        if self._is_keyboard_control_enabled:
            self._update_intents_for_robot()
        glutPostRedisplay()

    def _visible(self, vis):
        # Called from OpenGL when visibility changes (windows are either visible
        # or completely invisible/hidden)
        if vis == GLUT_VISIBLE:
            glutIdleFunc(self._idle)
        else:
            glutIdleFunc(None)

    def _draw_memory_map(self):
        # Update the renderable map if new data is available, and
        # render the latest map received.
        new_nav_memory_map = None
        try:
            new_nav_memory_map = self._nav_memory_map_queue.popleft()
        except IndexError:
            # no new nav map - queue is empty
            pass

        # Rebuild the renderable map if it has changed
        if new_nav_memory_map is not None:
            cen = new_nav_memory_map.center
            half_size = new_nav_memory_map.size * 0.5

            if self._nav_memory_map_display_list is None:
                self._nav_memory_map_display_list = glGenLists(1)
            glNewList(self._nav_memory_map_display_list, GL_COMPILE)

            glPushMatrix()

            color_light_gray = (0.65, 0.65, 0.65)
            glColor3f(*color_light_gray)
            glBegin(GL_LINE_STRIP)
            glVertex3f(cen.x + half_size, cen.y + half_size, cen.z)  # TL
            glVertex3f(cen.x + half_size, cen.y - half_size, cen.z)  # TR
            glVertex3f(cen.x - half_size, cen.y - half_size, cen.z)  # BR
            glVertex3f(cen.x - half_size, cen.y + half_size, cen.z)  # BL
            glVertex3f(cen.x + half_size, cen.y + half_size,
                       cen.z)  # TL (close loop)
            glEnd()

            def color_for_content(content):
                nct = nav_memory_map.NodeContentTypes
                colors = {nct.Unknown.id: (0.3, 0.3, 0.3),         # dark gray
                          nct.ClearOfObstacle.id: (0.0, 1.0, 0.0), # green
                          nct.ClearOfCliff.id: (0.0, 0.5, 0.0),    # dark green
                          nct.ObstacleCube.id: (1.0, 0.0, 0.0),    # red
                          nct.ObstacleCharger.id: (1.0, 0.5, 0.0), # orange
                          nct.Cliff.id: (0.0, 0.0, 0.0),           # black
                          nct.VisionBorder.id: (1.0, 1.0, 0.0)     # yellow
                          }

                col = colors.get(content.id)
                if col is None:
                    logger.error("Unhandled content type %s" % str(content))
                    col = (1.0, 1.0, 1.0)  # white
                return col

            fill_z = cen.z - 0.4

            def _recursive_draw(grid_node: nav_memory_map.NavMemoryMapGridNode):
                if grid_node.children is not None:
                    for child in grid_node.children:
                        _recursive_draw(child)
                else:
                    # leaf node - render as a quad
                    map_alpha = 0.5
                    cen = grid_node.center
                    half_size = grid_node.size * 0.5

                    # Draw outline
                    glColor4f(*color_light_gray, 1.0)  # fully opaque
                    glBegin(GL_LINE_STRIP)
                    glVertex3f(cen.x + half_size, cen.y + half_size, cen.z)
                    glVertex3f(cen.x + half_size, cen.y - half_size, cen.z)
                    glVertex3f(cen.x - half_size, cen.y - half_size, cen.z)
                    glVertex3f(cen.x - half_size, cen.y + half_size, cen.z)
                    glVertex3f(cen.x + half_size, cen.y + half_size, cen.z)
                    glEnd()

                    # Draw filled contents
                    glColor4f(*color_for_content(grid_node.content), map_alpha)
                    glBegin(GL_TRIANGLE_STRIP)
                    glVertex3f(cen.x + half_size, cen.y + half_size, fill_z)
                    glVertex3f(cen.x + half_size, cen.y - half_size, fill_z)
                    glVertex3f(cen.x - half_size, cen.y + half_size, fill_z)
                    glVertex3f(cen.x - half_size, cen.y - half_size, fill_z)
                    glEnd()

            _recursive_draw(new_nav_memory_map.root_node)

            glPopMatrix()
            glEndList()
        else:
            # The source data hasn't changed - keep using the same call list
            pass

        if self._nav_memory_map_display_list is not None:
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glEnable(GL_BLEND)
            glPushMatrix()
            glCallList(self._nav_memory_map_display_list)
            glPopMatrix()


    def _draw_cozmo(self, robot_frame):
        if self.cozmo_object is None:
            return

        robot_pose = robot_frame.pose
        robot_head_angle = robot_frame.head_angle
        robot_lift_position = robot_frame.lift_position

        # Angle of the lift in the object's initial default pose.
        LIFT_ANGLE_IN_DEFAULT_POSE = -11.36

        robot_matrix = robot_pose.to_matrix()
        head_angle = robot_head_angle.degrees
        # Get the angle of Cozmo's lift for rendering - we subtract the angle
        # of the lift in the default pose in the object, and apply the inverse
        # rotation
        lift_angle = -(robot_lift_position.angle.degrees - LIFT_ANGLE_IN_DEFAULT_POSE)

        glPushMatrix()
        glEnable(GL_LIGHTING)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        glMultMatrixf(robot_matrix.in_row_order)

        robot_scale_amt = 10.0  # cm to mm
        glScalef(robot_scale_amt, robot_scale_amt, robot_scale_amt)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # Pivot offset for where the fork rotates around itself
        FORK_PIVOT_X = 3.0
        FORK_PIVOT_Z = 3.4

        # Offset for the axel that the upper arm rotates around.
        UPPER_ARM_PIVOT_X = -3.73
        UPPER_ARM_PIVOT_Z = 4.47

        # Offset for the axel that the lower arm rotates around.
        LOWER_ARM_PIVOT_X = -3.74
        LOWER_ARM_PIVOT_Z = 3.27

        # Offset for the pivot that the head rotates around.
        HEAD_PIVOT_X = -1.1
        HEAD_PIVOT_Z = 4.75

        # Render the static body meshes - first the main body:
        glCallList(self.cozmo_object.meshes["body_geo"])
        # Render the left treads and wheels
        glCallList(self.cozmo_object.meshes["trackBase_L_geo"])
        glCallList(self.cozmo_object.meshes["wheel_BL_geo"])
        glCallList(self.cozmo_object.meshes["wheel_FL_geo"])
        glCallList(self.cozmo_object.meshes["tracks_L_geo"])
        # Render the right treads and wheels
        glCallList(self.cozmo_object.meshes["trackBase_R_geo"])
        glCallList(self.cozmo_object.meshes["wheel_BR_geo"])
        glCallList(self.cozmo_object.meshes["wheel_FR_geo"])
        glCallList(self.cozmo_object.meshes["tracks_R_geo"])

        # Render the fork at the front (but not the arms)
        glPushMatrix()
        # The fork rotates first around upper arm (to get it to the correct position).
        glTranslatef(UPPER_ARM_PIVOT_X, 0.0, UPPER_ARM_PIVOT_Z)
        glRotatef(lift_angle, 0, 1, 0)
        glTranslatef(-UPPER_ARM_PIVOT_X, 0.0, -UPPER_ARM_PIVOT_Z)
        # The fork then rotates back around itself as it always hangs vertically.
        glTranslatef(FORK_PIVOT_X, 0.0, FORK_PIVOT_Z)
        glRotatef(-lift_angle, 0, 1, 0)
        glTranslatef(-FORK_PIVOT_X, 0.0, -FORK_PIVOT_Z)
        # Render
        glCallList(self.cozmo_object.meshes["fork_geo"])
        glPopMatrix()

        # Render the upper arms:
        glPushMatrix()
        # Rotate the upper arms around the upper arm joint
        glTranslatef(UPPER_ARM_PIVOT_X, 0.0, UPPER_ARM_PIVOT_Z)
        glRotatef(lift_angle, 0, 1, 0)
        glTranslatef(-UPPER_ARM_PIVOT_X, 0.0, -UPPER_ARM_PIVOT_Z)
        # Render
        glCallList(self.cozmo_object.meshes["uprArm_L_geo"])
        glCallList(self.cozmo_object.meshes["uprArm_geo"])
        glPopMatrix()

        # Render the lower arms:
        glPushMatrix()
        # Rotate the lower arms around the lower arm joint
        glTranslatef(LOWER_ARM_PIVOT_X, 0.0, LOWER_ARM_PIVOT_Z)
        glRotatef(lift_angle, 0, 1, 0)
        glTranslatef(-LOWER_ARM_PIVOT_X, 0.0, -LOWER_ARM_PIVOT_Z)
        # Render
        glCallList(self.cozmo_object.meshes["lwrArm_L_geo"])
        glCallList(self.cozmo_object.meshes["lwrArm_R_geo"])
        glPopMatrix()

        # Render the head:
        glPushMatrix()
        # Rotate the head around the pivot
        glTranslatef(HEAD_PIVOT_X, 0.0, HEAD_PIVOT_Z)
        glRotatef(-head_angle, 0, 1, 0)
        glTranslatef(-HEAD_PIVOT_X, 0.0, -HEAD_PIVOT_Z)
        # Render all of the head meshes
        glCallList(self.cozmo_object.meshes["head_geo"])
        # Screen
        glCallList(self.cozmo_object.meshes["backScreen_mat"])
        glCallList(self.cozmo_object.meshes["screenEdge_geo"])
        glCallList(self.cozmo_object.meshes["overscan_1_geo"])
        # Eyes
        glCallList(self.cozmo_object.meshes["eye_L_geo"])
        glCallList(self.cozmo_object.meshes["eye_R_geo"])
        # Eyelids
        glCallList(self.cozmo_object.meshes["eyeLid_R_top_geo"])
        glCallList(self.cozmo_object.meshes["eyeLid_L_top_geo"])
        glCallList(self.cozmo_object.meshes["eyeLid_L_btm_geo"])
        glCallList(self.cozmo_object.meshes["eyeLid_R_btm_geo"])
        # Face cover (drawn last as it's translucent):
        glCallList(self.cozmo_object.meshes["front_Screen_geo"])
        glPopMatrix()

        glDisable(GL_LIGHTING)
        glPopMatrix()


    def _draw_unit_cube(self, color, draw_solid):
        glColor(color)

        if draw_solid:
            ambient_color = [color[0]*0.1, color[1]*0.1, color[2]*0.1, 1.0]
        else:
            ambient_color = color
        glMaterialfv(GL_FRONT, GL_AMBIENT, ambient_color)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, color)
        glMaterialfv(GL_FRONT, GL_SPECULAR,  color)

        glMaterialfv(GL_FRONT, GL_SHININESS, 10.0);

        if draw_solid:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glCallList(self.unit_cube)


    def _display_3d_view(self, window):
        glutSetWindow(window.gl_window)

        # Clear the screen and the depth buffer
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set up the projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        fov = 45.0
        aspect_ratio = window.width / window.height
        near_clip_plane = 1.0
        far_clip_plane = 1000.0
        gluPerspective(fov, aspect_ratio, near_clip_plane, far_clip_plane)

        # Switch to model matrix for rendering everything
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Add a light near the origin
        light_ambient = [1.0, 1.0, 1.0, 1.0]
        light_diffuse = [1.0, 1.0, 1.0, 1.0]
        light_specular = [1.0, 1.0, 1.0, 1.0]
        glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)
        light_pos = [0, 20, 10, 1]
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glEnable(GL_LIGHT0)

        glScalef(0.1, 0.1, 0.1)  # mm to cm

        # Orient the camera
        self._calculate_camera_pos()

        gluLookAt(*self._camera_pos.x_y_z,
                  *self._camera_look_at.x_y_z,
                  *self._camera_up.x_y_z)

        # Update the latest world frame if there is a new one available
        try:
            world_frame = self._world_frame_queue.popleft()  # type: WorldRenderFrame
            self._latest_world_frame = world_frame
        except IndexError:
            world_frame = self._latest_world_frame
            pass

        if world_frame is not None:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            glEnable(GL_NORMALIZE)  # to re-scale scaled normals

            robot_frame = world_frame.robot_frame
            robot_pose = robot_frame.pose

            # Render the cubes
            for i in range(3):
                cube_obj = self.cube_objects[i]
                cube_frame = world_frame.cube_frames[i]
                if cube_frame is None:
                    continue

                cube_pose = cube_frame.pose
                if cube_pose is not None and cube_pose.is_comparable(robot_pose):
                    glPushMatrix()

                    # TODO if cube_pose.is_accurate is False, render half-translucent?
                    #  (This would require using a shader, or having duplicate objects)

                    cube_matrix = cube_pose.to_matrix()
                    glMultMatrixf(cube_matrix.in_row_order)

                    # Cube is drawn slightly larger than the 10mm to 1 cm scale, as the model looks small otherwise
                    cube_scale_amt = 10.7
                    glScalef(cube_scale_amt, cube_scale_amt, cube_scale_amt)

                    cube_obj.draw_all()
                    glPopMatrix()

            glBindTexture(GL_TEXTURE_2D, 0)

            for face in world_frame.face_frames:
                face_pose = face.pose
                if face_pose is not None and face_pose.is_comparable(robot_pose):
                    glPushMatrix()
                    face_matrix = face_pose.to_matrix()
                    glMultMatrixf(face_matrix.in_row_order)

                    # Approximate size of a head
                    glScalef(100, 25, 100)

                    FACE_OBJECT_COLOR = [0.5, 0.5, 0.5, 1.0]
                    draw_solid = face.time_since_last_seen < 30
                    self._draw_unit_cube(FACE_OBJECT_COLOR, draw_solid)

                    glPopMatrix()

            for obj in world_frame.custom_object_frames:
                obj_pose = obj.pose
                if obj_pose is not None and obj_pose.is_comparable(robot_pose):
                    glPushMatrix()
                    obj_matrix = obj_pose.to_matrix()
                    glMultMatrixf(obj_matrix.in_row_order)

                    glScalef(obj.x_size_mm * 0.5,
                             obj.y_size_mm * 0.5,
                             obj.z_size_mm * 0.5)

                    # Only draw solid object for observable custom objects

                    if obj.is_fixed:
                        # fixed objects are drawn as transparent outlined boxes to make
                        # it clearer that they have no effect on vision.
                        FIXED_OBJECT_COLOR = [1.0, 0.7, 0.0, 1.0]
                        self._draw_unit_cube(FIXED_OBJECT_COLOR, False)
                    else:
                        CUSTOM_OBJECT_COLOR = [1.0, 0.3, 0.3, 1.0]
                        self._draw_unit_cube(CUSTOM_OBJECT_COLOR, True)

                    glPopMatrix()

            glDisable(GL_LIGHTING)

            self._draw_cozmo(robot_frame)

        if self._show_controls:
            self._draw_controls()

        # Draw the (translucent) nav map last so it's sorted correctly against opaque geometry
        self._draw_memory_map()

        glutSwapBuffers()

    def _draw_controls(self):
        try:
            GLUT_BITMAP_9_BY_15
        except NameError:
            pass
        else: 
            self._draw_text(GLUT_BITMAP_9_BY_15, self._instructions, 10, 10)

    def _draw_text(self, font, input, x, y, line_height=16, r=1.0, g=1.0, b=1.0):
        '''Render text based on window position. The origin is in the bottom-left.'''
        glColor3f(r, g, b)
        glWindowPos2f(x,y)
        input_list = input.split('\n')
        y = y + (line_height * (len(input_list) -1))
        for line in input_list:
            glWindowPos2f(x, y)
            y -= line_height
            for ch in line:
                glutBitmapCharacter(font, ctypes.c_int(ord(ch)))

    def _display_camera_view(self, window):
        glutSetWindow(window.gl_window)

        if self._camera_view_texture is None:
            self._camera_view_texture = DynamicTexture()

        target_width = window.width
        target_height = window.height
        target_aspect = 320 / 240  # (Camera-feed resolution and aspect ratio)
        max_u = 1.0
        max_v = 1.0
        if (target_width / target_height) < target_aspect:
            target_height = target_width / target_aspect
            max_v *= target_height / window.height
        elif (target_width / target_height) > target_aspect:
            target_width = target_height * target_aspect
            max_u *= target_width / window.width
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_TEXTURE_2D)

        # Try getting a new image if one has been added
        image = None
        try:
            image = self._img_queue.popleft()
        except IndexError:
            # no new image - queue is empty
            pass

        if image:
            # There's a new image - update the texture
            self._camera_view_texture.update(image)
        else:
            # keep using the most recent texture
            self._camera_view_texture.bind()

        # Display the image as a tri-strip with 4 vertices
        glBegin(GL_TRIANGLE_STRIP)
        # (0,0) = Top Left, (1,1) = Bottom Right
        # left, bottom
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-max_u, -max_v)
        # right, bottom
        glTexCoord2f(1.0, 1.0)
        glVertex2f(max_u, -max_v)
        # left, top
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-max_u, max_v)
        # right, top
        glTexCoord2f(1.0, 0.0)
        glVertex2f(max_u, max_v)
        glEnd()

        glDisable(GL_TEXTURE_2D)

        glutSwapBuffers()

    def _display(self):
        try:
            self._display_3d_view(self.main_window)

            if self.viewer_window:
                self._display_camera_view(self.viewer_window)
        except KeyboardInterrupt:
            logger.info("_display caught KeyboardInterrupt - exitting")
            self._request_exit()

    def _key_byte_to_lower(self, key):
        # Convert bytes-object (representing keyboard character) to lowercase equivalent
        if (key >= b'A') and (key <= b'Z'):
            lowercase_key = ord(key) - ord(b'A') + ord(b'a')
            lowercase_key = bytes([lowercase_key])
            return lowercase_key
        return key

    def _on_key_up(self, key, x, y):
        key = self._key_byte_to_lower(key)
        self._update_modifier_keys()
        self._is_key_pressed[key] = False

    def _on_key_down(self, key, x, y):
        key = self._key_byte_to_lower(key)
        self._update_modifier_keys()
        self._is_key_pressed[key] = True

        if ord(key) == 9:  # Tab
            # Set Look-At point to current robot position
            world_frame = self._latest_world_frame
            if world_frame is not None:
                robot_pos = world_frame.robot_frame.pose.position
                self._camera_look_at.set_to(robot_pos)
        elif ord(key) == 27:  # Escape key
            self._request_exit()
        elif ord(key) == 72 or ord(key) == 104: # H key
            self._show_controls = not self._show_controls


    def _on_special_key_up(self, key, x, y):
        self._update_modifier_keys()

    def _on_special_key_down(self, key, x, y):
        self._update_modifier_keys()

    def _on_mouse_button(self, button, state, x, y):
        # Don't update modifier keys- reading modifier keys is unreliable
        # from _on_mouse_button (for LMB down/up), only SHIFT key seems to read there
        #self._update_modifier_keys()
        is_down = (state == GLUT_DOWN)
        self._is_mouse_down[button] = is_down
        self._mouse_pos = util.Vector2(x, y)

    def _on_mouse_move_internal(self, x, y, is_active):
        # is_active is True if this is not passive (i.e. a mouse button was down)
        last_mouse_pos = self._mouse_pos
        self._mouse_pos = util.Vector2(x, y)
        if last_mouse_pos is None:
            # First mouse update - ignore (we need a delta of mouse positions)
            return

        left_button = self._is_mouse_down.get(GLUT_LEFT_BUTTON, False)
        # For laptop and other 1-button mouse users, treat 'x' key as a right mouse button too
        right_button = (self._is_mouse_down.get(GLUT_RIGHT_BUTTON, False) or
                        self._is_key_pressed.get(b'x', False))

        MOUSE_SPEED_SCALAR = 1.0  # general scalar for all mouse movement sensitivity
        MOUSE_ROTATE_SCALAR = 0.025  # additional scalar for rotation sensitivity
        mouse_delta = (self._mouse_pos - last_mouse_pos) * MOUSE_SPEED_SCALAR

        if left_button and right_button:
            # Move up/down
            self._camera_look_at._z -= mouse_delta.y
        elif right_button:
            # Move forward/back and left/right
            pitch = self._camera_pitch
            yaw = self._camera_yaw
            camera_offset = util.Vector3(math.cos(yaw), math.sin(yaw), math.sin(pitch))

            heading = math.atan2(camera_offset.y, camera_offset.x)

            half_pi = math.pi * 0.5
            self._camera_look_at._x += mouse_delta.x * math.cos(heading + half_pi)
            self._camera_look_at._y += mouse_delta.x * math.sin(heading + half_pi)

            self._camera_look_at._x += mouse_delta.y * math.cos(heading)
            self._camera_look_at._y += mouse_delta.y * math.sin(heading)
        elif left_button:
            if self._is_key_pressed.get(b'z', False):
                # Zoom in/out
                self._camera_distance = max(0.1, self._camera_distance + mouse_delta.y)
            else:
                # Adjust the Camera pitch and yaw
                self._camera_pitch = (self._camera_pitch - (mouse_delta.y * MOUSE_ROTATE_SCALAR))
                self._camera_yaw = (self._camera_yaw + (mouse_delta.x * MOUSE_ROTATE_SCALAR)) % (2.0 * math.pi)
                # Clamp pitch to slightyly less than pi/2 to avoid lock/errors at full up/down
                max_rotation = math.pi * 0.49
                self._camera_pitch = max(-max_rotation, min(max_rotation, self._camera_pitch))

    def _on_mouse_move(self, x, y):
        # Mouse movement when at least one button down
        self._on_mouse_move_internal(x, y, True)

    def _on_mouse_move_passive(self, x, y):
        # Mouse movement when no button down
        self._on_mouse_move_internal(x, y, False)

    def init_display(self):
        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)

        self.main_window.init_display()

        glutDisplayFunc(self._display)  # Note: both windows call the same DisplayFunc
        glutKeyboardFunc(self._on_key_down)
        glutSpecialFunc(self._on_special_key_down)

        # [Keyboard/Special]Up methods aren't supported on some old GLUT implementations
        has_keyboard_up = False
        has_special_up = False
        try:
            if bool(glutKeyboardUpFunc):
                glutKeyboardUpFunc(self._on_key_up)
                has_keyboard_up = True
            if bool(glutSpecialUpFunc):
                glutSpecialUpFunc(self._on_special_key_up)
                has_special_up = True
        except OpenGL.error.NullFunctionError:
            # Methods aren't available on this GLUT version
            pass

        if not has_keyboard_up or not has_special_up:
            # Warn on old GLUT implementations that don't implement much of the interface.
            logger.warning("Warning: Old GLUT implementation detected - keyboard remote control of Cozmo disabled."
                            "We recommend installing freeglut. %s", _glut_install_instructions())
            self._is_keyboard_control_enabled = False
        else:
            self._is_keyboard_control_enabled = True

        try:
            GLUT_BITMAP_9_BY_15
        except NameError:
            logger.warning("Warning: GLUT font not detected. Help message will be unavailable.")

        glutMouseFunc(self._on_mouse_button)
        glutMotionFunc(self._on_mouse_move)
        glutPassiveMotionFunc(self._on_mouse_move_passive)

        glutIdleFunc(self._idle)
        glutVisibilityFunc(self._visible)

        # Load 3D objects

        _cozmo_obj = LoadedObjFile("cozmo.obj")
        self.cozmo_object = RenderableObject(_cozmo_obj)

        # Load the cubes, reusing the same file geometry for all 3.
        _cube_obj = LoadedObjFile("cube.obj")
        self.cube_objects.append(RenderableObject(_cube_obj))
        self.cube_objects.append(RenderableObject(_cube_obj, override_mtl=LoadMtlFile("cube2.mtl")))
        self.cube_objects.append(RenderableObject(_cube_obj, override_mtl=LoadMtlFile("cube3.mtl")))

        self.unit_cube = _make_unit_cube()

        if self.viewer_window:
            self.viewer_window.init_display()
            glutDisplayFunc(self._display)  # Note: both windows call the same DisplayFunc

    def mainloop(self):
        self.init_display()

        # use a non-blocking update loop if possible to make exit conditions
        # easier (not supported on all GLUT versions).
        if bool(glutCheckLoop):
            while not self._exit_requested:
                glutCheckLoop()
        else:
            # This blocks until quit
            glutMainLoop()

        if self._exit_requested:
            # Pass the keyboard interrupt on to SDK so that it can close cleanly
            raise KeyboardInterrupt

    async def connect(self, sdk_conn):
        sdk_robot = await sdk_conn.wait_for_robot()

        # Note: OpenGL and SDK are on different threads, so we deliberately don't
        # store a reference to the robot here, as we should only access it from
        # events called on the SDK thread (where we can then thread-safely move
        # the data into OpenGL)

        self._robot_state_handler = sdk_robot.world.add_event_handler(
            robot.EvtRobotStateUpdated, self.on_robot_state_update)

        if self.viewer_window is not None:
            # Automatically enable camera stream when viewer window is used.
            sdk_robot.camera.image_stream_enabled = True
            self._image_handler = sdk_robot.world.add_event_handler(
                world.EvtNewCameraImage, self.on_new_camera_image)
        # Automatically enable streaming of the nav memory map when using the
        # viewer (can be overridden by user application after connection).
        sdk_robot.world.request_nav_memory_map(0.5)
        self._nav_map_handler = sdk_robot.world.add_event_handler(
            nav_memory_map.EvtNewNavMemoryMap, self.on_new_nav_memory_map)

    def disconnect(self):
        """Called from the SDK when the program is complete and it's time to exit."""
        if self._image_handler:
            self._image_handler.disable()
            self._image_handler = None
        if self._nav_map_handler:
            self._nav_map_handler.disable()
            self._nav_map_handler = None
        if self._robot_state_handler:
            self._robot_state_handler.disable()
            self._robot_state_handler = None
        if not self._exit_requested:
            self._request_exit()

    def _update_robot_remote_control(self, robot):
        # Called on SDK thread, for controlling robot from input intents
        # pushed from the OpenGL thread.
        try:
            input_intents = self._input_intent_queue.popleft()  # type: RobotControlIntents
        except IndexError:
            # no new input intents - do nothing
            return

        # Track last-used intents so that we only issue motor controls
        # if different from the last frame (to minimize it fighting with an SDK
        # program controlling the robot):
        old_intents = self._last_robot_control_intents
        self._last_robot_control_intents = input_intents

        if robot.is_on_charger:
            # Cozmo is stuck on the charger
            if input_intents.left_wheel_speed > 0 and input_intents.right_wheel_speed > 0:
                # User is trying to drive forwards (off the charger) - issue an explicit drive off action
                try:
                    # don't wait for action to complete
                    robot.drive_off_charger_contacts(in_parallel=True)
                except RobotBusy:
                    # Robot is busy doing another action - try again next time we get a drive impulse
                    pass

        if ((old_intents.left_wheel_speed != input_intents.left_wheel_speed) or
            (old_intents.right_wheel_speed != input_intents.right_wheel_speed)):
            robot.drive_wheel_motors(input_intents.left_wheel_speed,
                                     input_intents.right_wheel_speed,
                                     input_intents.left_wheel_speed * 4,
                                     input_intents.right_wheel_speed * 4)

        if (old_intents.lift_speed != input_intents.lift_speed):
            robot.move_lift(input_intents.lift_speed)

        if (old_intents.head_speed != input_intents.head_speed):
            robot.move_head(input_intents.head_speed)

    def on_robot_state_update(self, evt, *, robot, **kw):
        # Called from SDK whenever the robot state is updated (so i.e. every engine tick).
        # Note: This is called from the SDK thread, so only access safe things
        # We can safely capture any robot and world state here, and push to OpenGL
        # (main) thread via a thread-safe queue.
        world_frame = WorldRenderFrame(robot)
        self._world_frame_queue.append(world_frame)

        # We update remote control of the robot here too as it's the one
        # method that's called frequently on the SDK thread.
        self._update_robot_remote_control(robot)

    def on_new_camera_image(self, evt, *, image, **kw):
        # Called from SDK whenever a new image is available
        # Note: This is called from the SDK thread, so only access safe things:
        # viewer_window will already be created, and reading width/height is safe
        # (worst case it'll be a frame old, or e.g just width/height updated)
        fit_size=(self.viewer_window.width, self.viewer_window.height)
        annotated_image = image.annotate_image(fit_size=fit_size)
        self._img_queue.append(annotated_image)

    def on_new_nav_memory_map(self, evt, *, nav_memory_map, **kw):
        # Called from SDK whenever a new nav memory map is available
        # Note: This is called from the SDK thread, so only access safe things
        self._nav_memory_map_queue.append(nav_memory_map)
