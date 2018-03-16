# Copyright (c) 2016-2017 Anki, Inc.
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

'''Utility classes and functions.'''


# __all__ should order by constants, event classes, other classes, functions.
# (util keeps class related functions close to their associated class)
__all__ = ['Angle', 'degrees', 'radians',
           'ImageBox',
           'Distance', 'distance_mm', 'distance_inches', 'Matrix44',
           'Pose', 'pose_quaternion', 'pose_z_angle',
           'Position', 'Quaternion',
           'Rotation', 'rotation_quaternion', 'rotation_z_angle',
           'angle_z_to_quaternion',
           'Speed', 'speed_mmps',
           'Timeout', 'Vector2', 'Vector3']


import collections
import math
import time
from ._clad import _clad_to_engine_anki


class ImageBox(collections.namedtuple('ImageBox', 'top_left_x top_left_y width height')):
    '''Defines a bounding box within an image frame.

    This is used when objects, faces and pets are observed to denote where in
    the robot's camera view the object, face or pet actually appears.  It's then
    used by the :mod:`cozmo.annotate` module to show an outline of a box around
    the object, face or pet.

    .. py:attribute:: width

        float - The width of the box.

    .. py:attribute:: height

        float - The height of the box.
    '''
    __slots__ = ()

    @classmethod
    def _create_from_clad_rect(cls, img_rect):
        return cls(img_rect.x_topLeft, img_rect.y_topLeft,
                   img_rect.width, img_rect.height)

    @property
    def left_x(self):
        """float: The x coordinate of the left of the box."""
        return self.top_left_x

    @property
    def right_x(self):
        """float: The x coordinate of the right of the box."""
        return self.top_left_x + self.width

    @property
    def top_y(self):
        """float: The y coordinate of the top of the box."""
        return self.top_left_y

    @property
    def bottom_y(self):
        """float: The y coordinate of the bottom of the box."""
        return self.top_left_y + self.height

    @property
    def center(self):
        """(float, float): The x,y coordinates of the center of the box."""
        cen_x = self.top_left_x + (self.width * 0.5)
        cen_y = self.top_left_y + (self.height * 0.5)
        return cen_x, cen_y

    def __mul__(self, other):
        return ImageBox(self[0] * other, self[1] * other, self[2] * other, self[3] * other)


class Angle:
    '''Represents an angle.

    Use the :func:`degrees` or :func:`radians` convenience methods to generate
    an Angle instance.

    Args:
        radians (float): The number of radians the angle should represent
            (cannot be combined with ``degrees``)
        degrees (float): The number of degress the angle should represent
            (cannot be combined with ``radians``)
    '''

    __slots__ = ('_radians')

    def __init__(self, radians=None, degrees=None):
        if radians is None and degrees is None:
            raise ValueError("Expected either the degrees or radians keyword argument")
        if radians and degrees:
            raise ValueError("Expected either the degrees or radians keyword argument, not both")

        if degrees is not None:
            radians = degrees * math.pi / 180
        self._radians = float(radians)

    def __repr__(self):
        return "<%s %.2f radians (%.2f degrees)>" % (self.__class__.__name__, self.radians, self.degrees)

    def __add__(self, other):
        if not isinstance(other, Angle):
            raise TypeError("Unsupported type for + expected Angle")
        return radians(self.radians + other.radians)

    def __sub__(self, other):
        if not isinstance(other, Angle):
            raise TypeError("Unsupported type for - expected Angle")
        return radians(self.radians - other.radians)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported type for * expected number")
        return radians(self.radians * other)

    def __truediv__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported type for / expected number")
        return radians(self.radians / other)

    def _cmp_int(self, other):
        if not isinstance(other, Angle):
            raise TypeError("Unsupported type for comparison expected Angle")
        return self.radians - other.radians

    def __eq__(self, other):
        return self._cmp_int(other) == 0

    def __ne__(self, other):
        return self._cmp_int(other) != 0

    def __gt__(self, other):
        return self._cmp_int(other) > 0

    def __lt__(self, other):
        return self._cmp_int(other) < 0

    def __ge__(self, other):
        return self._cmp_int(other) >= 0

    def __le__(self, other):
        return self._cmp_int(other) <= 0

    @property
    def radians(self):
        '''float: The angle in radians.'''
        return self._radians

    @property
    def degrees(self):
        '''float: The angle in degrees.'''
        return self._radians / math.pi * 180

    @property
    def abs_value(self):
        """:class:`cozmo.util.Angle`: The absolute value of the angle.
        
        If the Angle is positive then it returns a copy of this Angle, otherwise it returns -Angle.
        """
        return Angle(radians = abs(self._radians))


def degrees(degrees):
    '''Returns an :class:`cozmo.util.Angle` instance set to the specified number of degrees.'''
    return Angle(degrees=degrees)


def radians(radians):
    '''Returns an :class:`cozmo.util.Angle` instance set to the specified number of radians.'''
    return Angle(radians=radians)


class Distance:
    '''Represents a distance.

    The class allows distances to be returned in either millimeters or inches.

    Use the :func:`distance_inches` or :func:`distance_mm` convenience methods to generate
    a Distance instance.

    Args:
        distance_mm (float): The number of millimeters the distance should
            represent (cannot be combined with ``distance_inches``).
        distance_inches (float): The number of inches the distance should
            represent (cannot be combined with ``distance_mm``).
    '''

    __slots__ = ('_distance_mm')

    def __init__(self, distance_mm=None, distance_inches=None):
        if distance_mm is None and distance_inches is None:
            raise ValueError("Expected either the distance_mm or distance_inches keyword argument")
        if distance_mm and distance_inches:
            raise ValueError("Expected either the distance_mm or distance_inches keyword argument, not both")

        if distance_inches is not None:
            distance_mm = distance_inches * 25.4
        self._distance_mm = distance_mm

    def __repr__(self):
        return "<%s %.2f mm (%.2f inches)>" % (self.__class__.__name__, self.distance_mm, self.distance_inches)

    def __add__(self, other):
        if not isinstance(other, Distance):
            raise TypeError("Unsupported operand for + expected Distance")
        return distance_mm(self.distance_mm + other.distance_mm)

    def __sub__(self, other):
        if not isinstance(other, Distance):
            raise TypeError("Unsupported operand for - expected Distance")
        return distance_mm(self.distance_mm - other.distance_mm)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for * expected number")
        return distance_mm(self.distance_mm * other)

    def __truediv__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for / expected number")
        return distance_mm(self.distance_mm / other)

    @property
    def distance_mm(self):
        '''float: The distance in millimeters'''
        return self._distance_mm

    @property
    def distance_inches(self):
        '''float: The distance in inches'''
        return self._distance_mm / 25.4


def distance_mm(distance_mm):
    '''Returns an :class:`cozmo.util.Distance` instance set to the specified number of millimeters.'''
    return Distance(distance_mm=distance_mm)


def distance_inches(distance_inches):
    '''Returns an :class:`cozmo.util.Distance` instance set to the specified number of inches.'''
    return Distance(distance_inches=distance_inches)


class Speed:
    '''Represents a speed.

    This class allows speeds to be measured  in millimeters per second.

    Use :func:`speed_mmps` convenience methods to generate
    a Speed instance.

    Args:
        speed_mmps (float): The number of millimeters per second the speed
            should represent.
    '''

    __slots__ = ('_speed_mmps')

    def __init__(self, speed_mmps=None):
        if speed_mmps is None:
            raise ValueError("Expected speed_mmps keyword argument")
        self._speed_mmps = speed_mmps

    def __repr__(self):
        return "<%s %.2f mmps>" % (self.__class__.__name__, self.speed_mmps)

    def __add__(self, other):
        if not isinstance(other, Speed):
            raise TypeError("Unsupported operand for + expected Speed")
        return speed_mmps(self.speed_mmps + other.speed_mmps)

    def __sub__(self, other):
        if not isinstance(other, Speed):
            raise TypeError("Unsupported operand for - expected Speed")
        return speed_mmps(self.speed_mmps - other.speed_mmps)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for * expected number")
        return speed_mmps(self.speed_mmps * other)

    def __truediv__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for / expected number")
        return speed_mmps(self.speed_mmps / other)

    @property
    def speed_mmps(self):
        '''float: The speed in millimeters per second (mmps).'''
        return self._speed_mmps


def speed_mmps(speed_mmps):
    '''Returns an :class:`cozmo.util.Speed` instance set to the specified millimeters per second speed'''
    return Speed(speed_mmps=speed_mmps)


class Pose:
    '''Represents where an object is in the world.

    Use the :func:'pose_quaternion' to return pose in the form of
    position and rotation defined by a quaternion

    Use the :func:'pose_z_angle' to return pose in the form of
    position and rotation defined by rotation about the z axis

    When the engine is initialized, and whenever Cozmo is de-localized (i.e.
    whenever Cozmo no longer knows where he is - e.g. when he's picked up)
    Cozmo creates a new pose starting at (0,0,0) with no rotation, with
    origin_id incremented to show that these poses cannot be compared with
    earlier ones. As Cozmo drives around, his pose (and the pose of other
    objects he observes - e.g. faces, cubes etc.) is relative to this initial
    position and orientation.

    The coordinate space is relative to Cozmo, where Cozmo's origin is the
    point on the ground between Cozmo's two front wheels:

    The X axis is Cozmo's forward direction
    The Y axis is to Cozmo's left
    The Z axis is up

    Only poses of the same origin_id can safely be compared or operated on
    '''

    __slots__ = ('_position', '_rotation', '_origin_id', '_is_accurate')

    def __init__(self, x, y, z, q0=None, q1=None, q2=None, q3=None,
                 angle_z=None, origin_id=-1, is_accurate=True):
        self._position = Position(x,y,z)
        self._rotation = Quaternion(q0,q1,q2,q3,angle_z)
        self._origin_id = origin_id
        self._is_accurate = is_accurate

    @classmethod
    def _create_from_clad(cls, pose):
        return cls(pose.x, pose.y, pose.z,
                   q0=pose.q0, q1=pose.q1, q2=pose.q2, q3=pose.q3,
                   origin_id=pose.originID)

    @classmethod
    def _create_default(cls):
        return cls(0.0, 0.0, 0.0,
                   q0=1.0, q1=0.0, q2=0.0, q3=0.0,
                   origin_id=-1)

    def __repr__(self):
        return "<%s %s %s origin_id=%d>" % (self.__class__.__name__, self.position, self.rotation, self.origin_id)

    def __add__(self, other):
        if not isinstance(other, Pose):
            raise TypeError("Unsupported operand for + expected Pose")
        pos = self.position + other.position
        rot = self.rotation + other.rotation
        return pose_quaternion(pos.x, pos.y, pos.z, rot.q0, rot.q1, rot.q2, rot.q3)

    def __sub__(self, other):
        if not isinstance(other, Pose):
            raise TypeError("Unsupported operand for - expected Pose")
        pos = self.position - other.position
        rot = self.rotation - other.rotation
        return pose_quaternion(pos.x, pos.y, pos.z, rot.q0, rot.q1, rot.q2, rot.q3)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for * expected number")
        pos = self.position * other
        rot = self.rotation * other
        return pose_quaternion(pos.x, pos.y, pos.z, rot.q0, rot.q1, rot.q2, rot.q3)

    def __truediv__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for / expected number")
        pos = self.position / other
        rot = self.rotation / other
        return pose_quaternion(pos.x, pos.y, pos.z, rot.q0, rot.q1, rot.q2, rot.q3)

    def define_pose_relative_this(self, new_pose):
        '''Creates a new pose such that new_pose's origin is now at the location of this pose.

        Args:
            new_pose (:class:`cozmo.util.Pose`): The pose which origin is being changed.
        Returns:
            A :class:`cozmo.util.pose` object for which the origin was this pose's origin.
        '''

        if not isinstance(new_pose, Pose):
            raise TypeError("Unsupported type for new_origin, must be of type Pose")
        x,y,z = self.position.x_y_z
        angle_z = self.rotation.angle_z
        new_x,new_y,new_z = new_pose.position.x_y_z
        new_angle_z = new_pose.rotation.angle_z

        cos_angle = math.cos(angle_z.radians)
        sin_angle = math.sin(angle_z.radians)
        res_x = x + (cos_angle * new_x) - (sin_angle * new_y)
        res_y = y + (sin_angle * new_x) + (cos_angle * new_y)
        res_z = z + new_z
        res_angle = angle_z + new_angle_z
        return Pose(res_x, res_y, res_z, angle_z=res_angle, origin_id=self._origin_id)

    def encode_pose(self):
        x, y, z = self.position.x_y_z
        q0, q1, q2, q3 = self.rotation.q0_q1_q2_q3
        return _clad_to_engine_anki.PoseStruct3d(x, y, z, q0, q1, q2, q3, self.origin_id)

    def invalidate(self):
        '''Mark this pose as being invalid (unusable)'''
        self._origin_id = -1

    def is_comparable(self, other_pose):
        '''Are these two poses comparable.

        Poses are comparable if they're valid and having matching origin IDs.

        Args:
            other_pose (:class:`cozmo.util.Pose`): The other pose to compare against.
        Returns:
            bool: True if the two poses are comparable, False otherwise.
        '''
        return (self.is_valid and other_pose.is_valid and
                (self.origin_id == other_pose.origin_id))

    @property
    def is_valid(self):
        '''bool: Returns True if this is a valid, usable pose.'''
        return self.origin_id >= 0

    @property
    def position(self):
        ''':class:`cozmo.util.Position`: The position component of this pose.'''
        return self._position

    @property
    def rotation(self):
        ''':class:`cozmo.util.Rotation`: The rotation component of this pose.'''
        return self._rotation

    def to_matrix(self):
        """Convert the Pose to a Matrix44.

        Returns:
            :class:`cozmo.util.Matrix44`: A matrix representing this Pose's
            position and rotation.
        """
        return self.rotation.to_matrix(*self.position.x_y_z)

    @property
    def origin_id(self):
        '''int: An ID maintained by the engine which represents which coordinate frame this pose is in.'''
        return self._origin_id

    @origin_id.setter
    def origin_id(self, value):
        '''Allows this to be changed later in case it was not originally defined.'''
        if not isinstance(value, int):
            raise TypeError("The type of origin_id must be int")
        self._origin_id = value

    @property
    def is_accurate(self):
        '''bool: Returns True if this pose is valid and accurate.

        Poses are marked as inaccurate if we detect movement via accelerometer,
        or if they were observed from far enough away that we're less certain
        of the exact pose.
        '''
        return self.is_valid and self._is_accurate


def pose_quaternion(x, y, z, q0, q1, q2, q3, origin_id=0):
    '''Returns a :class:`cozmo.util.Pose` instance set to the pose given in quaternion format.'''
    return Pose(x, y, z, q0=q0, q1=q1, q2=q2, q3=q3, origin_id=origin_id)

def pose_z_angle(x, y, z, angle_z, origin_id=0):
    '''Returns a :class:`cozmo.util.Pose` instance set to the pose given in z angle format.'''
    return Pose(x, y, z, angle_z=angle_z, origin_id=origin_id)


class Matrix44:
    """A 4x4 Matrix for representing the rotation and/or position of an object in the world.
    
    Can be generated from a :class:`Quaternion` for a pure rotation matrix, or
    combined with a position for a full translation matrix, as done by
    :meth:`Pose.to_matrix`.
    """
    __slots__ = ('m00', 'm10', 'm20', 'm30',
                 'm01', 'm11', 'm21', 'm31',
                 'm02', 'm12', 'm22', 'm32',
                 'm03', 'm13', 'm23', 'm33')

    def __init__(self,
                 m00, m10, m20, m30,
                 m01, m11, m21, m31,
                 m02, m12, m22, m32,
                 m03, m13, m23, m33):
        self.m00 = m00
        self.m10 = m10
        self.m20 = m20
        self.m30 = m30

        self.m01 = m01
        self.m11 = m11
        self.m21 = m21
        self.m31 = m31

        self.m02 = m02
        self.m12 = m12
        self.m22 = m22
        self.m32 = m32

        self.m03 = m03
        self.m13 = m13
        self.m23 = m23
        self.m33 = m33

    def __repr__(self):
        return ("<%s: "
                "%.1f %.1f %.1f %.1f %.1f %.1f %.1f %.1f "
                "%.1f %.1f %.1f %.1f %.1f %.1f %.1f %.1f>" % (
                self.__class__.__name__, *self.in_row_order))

    @property
    def tabulated_string(self):
        """str: A multi-line string formatted with tabs to show the matrix contents."""
        return ("%.1f\t%.1f\t%.1f\t%.1f\n"
                "%.1f\t%.1f\t%.1f\t%.1f\n"
                "%.1f\t%.1f\t%.1f\t%.1f\n"
                "%.1f\t%.1f\t%.1f\t%.1f" % self.in_row_order)

    @property
    def in_row_order(self):
        """tuple of 16 floats: The contents of the matrix in row order."""
        return self.m00, self.m01, self.m02, self.m03,\
               self.m10, self.m11, self.m12, self.m13,\
               self.m20, self.m21, self.m22, self.m23,\
               self.m30, self.m31, self.m32, self.m33

    @property
    def in_column_order(self):
        """tuple of 16 floats: The contents of the matrix in column order."""
        return self.m00, self.m10, self.m20, self.m30,\
               self.m01, self.m11, self.m21, self.m31,\
               self.m02, self.m12, self.m22, self.m32,\
               self.m03, self.m13, self.m23, self.m33

    @property
    def forward_xyz(self):
        """tuple of 3 floats: The x,y,z components representing the matrix's forward vector."""
        return self.m00, self.m01, self.m02

    @property
    def left_xyz(self):
        """tuple of 3 floats: The x,y,z components representing the matrix's left vector."""
        return self.m10, self.m11, self.m12

    @property
    def up_xyz(self):
        """tuple of 3 floats: The x,y,z components representing the matrix's up vector."""
        return self.m20, self.m21, self.m22

    @property
    def pos_xyz(self):
        """tuple of 3 floats: The x,y,z components representing the matrix's position vector."""
        return self.m30, self.m31, self.m32

    def set_forward(self, x, y, z):
        """Set the x,y,z components representing the matrix's forward vector.

        Args:
            x (float): The X component.
            y (float): The Y component.
            z (float): The Z component.
        """
        self.m00 = x
        self.m01 = y
        self.m02 = z

    def set_left(self, x, y, z):
        """Set the x,y,z components representing the matrix's left vector.

        Args:
            x (float): The X component.
            y (float): The Y component.
            z (float): The Z component.
        """
        self.m10 = x
        self.m11 = y
        self.m12 = z

    def set_up(self, x, y, z):
        """Set the x,y,z components representing the matrix's up vector.

        Args:
            x (float): The X component.
            y (float): The Y component.
            z (float): The Z component.
        """
        self.m20 = x
        self.m21 = y
        self.m22 = z

    def set_pos(self, x, y, z):
        """Set the x,y,z components representing the matrix's position vector.

        Args:
            x (float): The X component.
            y (float): The Y component.
            z (float): The Z component.
        """
        self.m30 = x
        self.m31 = y
        self.m32 = z


class Quaternion:
    '''Represents the rotation of an object in the world. Can be generated with
    quaternion to define its rotation in 3d space, or with only a z axis rotation
    to define things limited to the x-y plane like Cozmo.

    Use the :func:`rotation_quaternion` to return rotation defined by a quaternion.

    Use the :func:`rotation_angle_z` to return rotation defined by an angle in the z axis.
    '''
    __slots__ = ('_q0', '_q1', '_q2', '_q3')

    def __init__(self, q0=None, q1=None, q2=None, q3=None, angle_z=None):
        is_quaternion = not (q0 is None) and not (q1 is None) and not (q2 is None) and not (q3 is None)

        if not is_quaternion and angle_z is None:
            raise ValueError("Expected either the q0 q1 q2 and q3 or angle_z keyword arguments")
        if is_quaternion and angle_z:
            raise ValueError("Expected either the q0 q1 q2 and q3 or angle_z keyword argument, not both")
        if angle_z is not None:
            if not isinstance(angle_z, Angle):
                raise TypeError("Unsupported type for angle_z expected Angle")
            q0,q1,q2,q3 = angle_z_to_quaternion(angle_z)

        self._q0, self._q1, self._q2, self._q3 = q0, q1, q2, q3

    def __repr__(self):
        return ("<%s q0: %.2f q1: %.2f q2: %.2f q3: %.2f (angle_z: %s)>" %
            (self.__class__.__name__, self.q0, self.q1, self.q2, self.q3, self.angle_z))

    def to_matrix(self, pos_x=0.0, pos_y=0.0, pos_z=0.0):
        """Convert the Quaternion to a 4x4 matrix representing this rotation.

        A position can also be provided to generate a full translation matrix.

        Args:
            pos_x (float): The x component for the position.
            pos_y (float): The y component for the position.
            pos_z (float): The z component for the position.

        Returns:
            :class:`cozmo.util.Matrix44`: A matrix representing this Quaternion's
            rotation, with the provided position (which defaults to 0,0,0).
        """
        # See https://en.wikipedia.org/wiki/Quaternions_and_spatial_rotation
        q0q0 = self.q0 * self.q0
        q1q1 = self.q1 * self.q1
        q2q2 = self.q2 * self.q2
        q3q3 = self.q3 * self.q3

        q0x2 = self.q0 * 2.0  # saves 2 multiplies
        q0q1x2 = q0x2 * self.q1
        q0q2x2 = q0x2 * self.q2
        q0q3x2 = q0x2 * self.q3
        q1x2 = self.q1 * 2.0  # saves 1 multiply
        q1q2x2 = q1x2 * self.q2
        q1q3x2 = q1x2 * self.q3
        q2q3x2 = 2.0 * self.q2 * self.q3

        m00 = (q0q0 + q1q1 - q2q2 - q3q3)
        m01 = (q1q2x2 + q0q3x2)
        m02 = (q1q3x2 - q0q2x2)

        m10 = (q1q2x2 - q0q3x2)
        m11 = (q0q0 - q1q1 + q2q2 - q3q3)
        m12 = (q0q1x2 + q2q3x2)

        m20 = (q0q2x2 + q1q3x2)
        m21 = (q2q3x2 - q0q1x2)
        m22 = (q0q0 - q1q1 - q2q2 + q3q3)

        return Matrix44(m00, m10, m20, pos_x,
                        m01, m11, m21, pos_y,
                        m02, m12, m22, pos_z,
                        0.0, 0.0, 0.0, 1.0)

    #These are only for angle_z because quaternion addition/subtraction is not relevant here
    def __add__(self, other):
        if not isinstance(other, Quaternion):
            raise TypeError("Unsupported operand for + expected Quaternion")
        return rotation_z_angle(self.angle_z + other.angle_z)

    def __sub__(self, other):
        if not isinstance(other, Quaternion):
            raise TypeError("Unsupported operand for - expected Quaternion")
        return rotation_z_angle(self.angle_z - other.angle_z)

    def __mul__(self, other):
        if not isinstance(other, (int,float)):
            raise TypeError("Unsupported operand for * expected number")
        return rotation_z_angle(self.angle_z * other)

    def __truediv__(self, other):
        if not isinstance(other, (int,float)):
            raise TypeError("Unsupported operand for / expected number")
        return rotation_z_angle(self.angle_z / other)

    @property
    def q0(self):
        '''float: The q0 (w) value of the quaternion.'''
        return self._q0

    @property
    def q1(self):
        '''float: The q1 (i) value of the quaternion.'''
        return self._q1

    @property
    def q2(self):
        '''float: The q2 (j) value of the quaternion.'''
        return self._q2

    @property
    def q3(self):
        '''float: The q3 (k) value of the quaternion.'''
        return self._q3

    @property
    def q0_q1_q2_q3(self):
        '''tuple of float: Contains all elements of the quaternion (q0,q1,q2,q3)'''
        return self._q0,self._q1,self._q2,self._q3

    @property
    def angle_z(self):
        '''class:`Angle`: The z Euler component of the object's rotation.

        Defined as the rotation in the z axis.
        '''
        q0,q1,q2,q3 = self.q0_q1_q2_q3
        return Angle(radians=math.atan2(2*(q1*q2+q0*q3), 1-2*(q2**2+q3**2)))

    @property
    def euler_angles(self):
        '''tuple of float: Euler angles of an object.

        Returns the pitch, yaw, roll Euler components of the object's
        rotation defined as rotations in the x, y, and z axis respectively.

        It interprets the rotations performed in the order: Z, Y, X
        '''
        # convert to matrix
        matrix = self.to_matrix()

        # normalize the magnitudes of cos(roll)*sin(pitch) (i.e. m12) and
        #   cos(roll)*cos(pitch) (ie. m22), to isolate cos(roll) to be compared
        #   against -sin(roll) (m02).  Unfortunately, this omits results with an
        #   absolute angle larger than 90 degrees on roll.
        absolute_cos_roll = math.sqrt(matrix.m12*matrix.m12+matrix.m22*matrix.m22)
        near_gimbal_lock = absolute_cos_roll < 1e-6
        if not near_gimbal_lock:
            # general case euler decomposition
            pitch = math.atan2(matrix.m22, matrix.m12)
            yaw = math.atan2(matrix.m00, matrix.m01)
            roll = math.atan2(absolute_cos_roll, -matrix.m02)
        else:
            # special case euler angle decomposition near gimbal lock
            pitch = math.atan2(matrix.m11, -matrix.m21)
            yaw = 0
            roll = math.atan2(absolute_cos_roll, -matrix.m02)

        # adjust roll to be consistent with how we orient the device
        roll = math.pi * 0.5 - roll
        if roll > math.pi:
            roll -= math.pi * 2

        return pitch, yaw, roll


class Rotation(Quaternion):
    '''An alias for :class:`Quaternion`'''
    __slots__ = ()


def rotation_quaternion(q0, q1, q2, q3):
    '''Returns a :class:`Rotation` instance set by a quaternion.'''
    return Quaternion(q0=q0, q1=q1, q2=q2, q3=q3)


def rotation_z_angle(angle_z):
    '''Returns a class:`Rotation` instance set by an angle in the z axis'''
    return Quaternion(angle_z=angle_z)


def angle_z_to_quaternion(angle_z):
    '''This function converts an angle in the z axis (Euler angle z component) to a quaternion.

    Args:
        angle_z (:class:`cozmo.util.Angle`): The z axis angle.

    Returns:
        q0,q1,q2,q3 (float, float, float, float): A tuple with all the members
            of a quaternion defined by angle_z.
    '''

    #Define the quaternion to be converted from a Euler angle (x,y,z) of 0,0,angle_z
    #These equations have their original equations above, and simplified implemented
    # q0 = cos(x/2)*cos(y/2)*cos(z/2) + sin(x/2)*sin(y/2)*sin(z/2)
    q0 = math.cos(angle_z.radians/2)
    # q1 = sin(x/2)*cos(y/2)*cos(z/2) - cos(x/2)*sin(y/2)*sin(z/2)
    q1 = 0
    # q2 = cos(x/2)*sin(y/2)*cos(z/2) + sin(x/2)*cos(y/2)*sin(z/2)
    q2 = 0
    # q3 = cos(x/2)*cos(y/2)*sin(z/2) - sin(x/2)*sin(y/2)*cos(z/2)
    q3 = math.sin(angle_z.radians/2)
    return q0,q1,q2,q3


class Vector2:
    '''Represents a 2D Vector (type/units aren't specified)

    Args:
        x (float): X component
        y (float): Y component
    '''

    __slots__ = ('_x', '_y')

    def __init__(self, x, y):
        self._x = x
        self._y = y

    def set_to(self, rhs):
        """Copy the x and y components of the given vector.

        Args:
            rhs (:class:`Vector2`): The right-hand-side of this assignment - the
                source vector to copy into this vector.
        """
        self._x = rhs.x
        self._y = rhs.y

    @property
    def x(self):
        '''float: The x component.'''
        return self._x

    @property
    def y(self):
        '''float: The y component.'''
        return self._y

    @property
    def x_y(self):
        '''tuple (float, float): The X, Y elements of the Vector2 (x,y)'''
        return self._x, self._y

    def __repr__(self):
        return "<%s x: %.2f y: %.2f>" % (self.__class__.__name__, self.x, self.y)

    def __add__(self, other):
        if not isinstance(other, Vector2):
            raise TypeError("Unsupported operand for + expected Vector2")
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        if not isinstance(other, Vector2):
            raise TypeError("Unsupported operand for - expected Vector2")
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for * expected number")
        return Vector2(self.x * other, self.y * other)

    def __truediv__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for / expected number")
        return Vector2(self.x / other, self.y / other)


class Vector3:
    '''Represents a 3D Vector (type/units aren't specified)

    Args:
        x (float): X component
        y (float): Y component
        z (float): Z component
    '''

    __slots__ = ('_x', '_y', '_z')

    def __init__(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z

    def set_to(self, rhs):
        """Copy the x, y and z components of the given vector.

        Args:
            rhs (:class:`Vector3`): The right-hand-side of this assignment - the
                source vector to copy into this vector.
        """
        self._x = rhs.x
        self._y = rhs.y
        self._z = rhs.z

    @property
    def x(self):
        '''float: The x component.'''
        return self._x

    @property
    def y(self):
        '''float: The y component.'''
        return self._y

    @property
    def z(self):
        '''float: The z component.'''
        return self._z

    @property
    def x_y_z(self):
        '''tuple (float, float, float): The X, Y, Z elements of the Vector3 (x,y,z)'''
        return self._x, self._y, self._z

    def __repr__(self):
        return "<%s x: %.2f y: %.2f z: %.2f>" % (self.__class__.__name__, self.x, self.y, self.z)

    def __add__(self, other):
        if not isinstance(other, Vector3):
            raise TypeError("Unsupported operand for + expected Vector3")
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        if not isinstance(other, Vector3):
            raise TypeError("Unsupported operand for - expected Vector3")
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for * expected number")
        return Vector3(self.x * other, self.y * other, self.z * other)

    def __truediv__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Unsupported operand for / expected number")
        return Vector3(self.x / other, self.y / other, self.z / other)


class Position(Vector3):
    '''Represents the position of an object in the world.

    A position consists of its x, y and z values in millimeters.

    Args:
        x (float): X position in millimeters
        y (float): Y position in millimeters
        z (float): Z position in millimeters
    '''
    __slots__ = ()


class Timeout:
    '''Utility class to keep track of a timeout condition.

    This measures a timeout from the point in time that the class
    is instantiated.

    Args:
        timeout (float): Amount of time (in seconds) allotted to pass before
            considering the timeout condition to be met.
        use_inf (bool): If True, then :attr:`remaining` will return
            :const:`math.inf` if `timeout` is None, else it will return
            `None`.
    '''
    def __init__(self, timeout=None, use_inf=False):
        self.start = time.time()
        self.timeout = timeout
        self.use_inf = use_inf

    @property
    def is_timed_out(self):
        '''bool: True if the timeout has expired.'''
        if self.timeout is None:
            return False
        return time.time() - self.start > self.timeout

    @property
    def remaining(self):
        '''float: The number of seconds remaining before reaching the timeout.

        Will return a number of zero or higher, even if the timer has
        since expired (it will never return a negative value).

        Will return None or math.inf (if ``use_inf`` was passed as ``True``
        to the constructor) if the original timeout was ``None``.
        '''
        if self.timeout is None:
            return math.inf if self.use_inf else None
        return max(0, self.timeout - (time.time() - self.start))
