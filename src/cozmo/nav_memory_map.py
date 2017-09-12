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

'''A 2D navigation memory map of the world around Cozmo.

Cozmo builds a memory map of the navigable world around him as he drives
around. This is mostly based on where objects are seen (the cubes, charger, and
any custom objects), and also includes where Cozmo detects cliffs/drops, and
visible edges (e.g. sudden changes in color).

This differs from a standard occupancy map in that it doesn't deal with
probabilities of occupancy, but instead encodes what type of content is there.

To use the map you must first call :meth:`cozmo.world.World.request_nav_memory_map`
with a positive frequency so that the data is streamed to the SDK.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['EvtNewNavMemoryMap',
           'NavMemoryMapGrid', 'NavMemoryMapGridNode',
           'NodeContentTypes']

from collections import namedtuple

from . import event
from . import logger
from . import util
from ._clad import CladEnumWrapper, _clad_to_game_iface


class EvtNewNavMemoryMap(event.Event):
    '''Dispatched when a new memory map is received.'''
    nav_memory_map = 'A NavMemoryMapGrid object'


class _NodeContentType(namedtuple('_NodeContentType', 'name id')):
    # Tuple mapping between CLAD ENodeContentTypeEnum name and ID
    # All instances will be members of ActionResults

    # Keep _NodeContentType as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'NodeContentTypes.%s' % self.name


class NodeContentTypes(CladEnumWrapper):
    """The content types for a :class:`NavMemoryMapGridNode`."""

    _clad_enum = _clad_to_game_iface.ENodeContentTypeEnum
    _entry_type = _NodeContentType

    #: The contents of the node is unknown.
    Unknown = _entry_type("Unknown", _clad_enum.Unknown)

    #: The node is clear of obstacles, because Cozmo has seen objects on the
    #: other side, but it might contain a cliff. The node will be marked as
    #: either :attr:`Cliff` or :attr:`ClearOfCliff` once Cozmo has driven there.
    ClearOfObstacle = _entry_type("ClearOfObstacle", _clad_enum.ClearOfObstacle)

    #: The node is clear of any cliffs (a sharp drop) or obstacles.
    ClearOfCliff = _entry_type("ClearOfCliff", _clad_enum.ClearOfCliff)

    #: The node contains a :class:`~cozmo.objects.LightCube`.
    ObstacleCube = _entry_type("ObstacleCube", _clad_enum.ObstacleCube)

    #: The node contains a :class:`~cozmo.objects.Charger`.
    ObstacleCharger = _entry_type("ObstacleCharger", _clad_enum.ObstacleCharger)

    #: The node contains a cliff (a sharp drop).
    Cliff = _entry_type("Cliff", _clad_enum.Cliff)

    #: The node contains a visible edge (based on the camera feed).
    VisionBorder = _entry_type("VisionBorder", _clad_enum.VisionBorder)

    # This entry is undocumented and not currently used
    _ObstacleProx = _entry_type("ObstacleProx", _clad_enum.ObstacleProx)


NodeContentTypes._init_class()


class NavMemoryMapGridNode:
    """A node in a :class:`NavMemoryMapGrid`.

    Leaf nodes contain content, all other nodes are split into 4 equally sized
    children.

    Child node indices are stored in the following X,Y orientation:

        +---+----+---+
        | ^ | 2  | 0 |
        +---+----+---+
        | Y | 3  | 1 |
        +---+----+---+
        |   | X->|   |
        +---+----+---+
    """
    def __init__(self, depth, size, center, parent):
        #: int: The depth of this node. I.e. how far down the quad-tree is it.
        self.depth = depth

        #: float: The size (width or length) of this square node.
        self.size = size

        #: :class:`~cozmo.util.Vector3`: The center of this node.
        self.center = center  # type: util.Vector3

        #: :class:`NavMemoryMapGridNode`: The parent of this node. Is ``None`` for the root node.
        self.parent = parent  # type: NavMemoryMapGridNode

        #: list of :class:`NavMemoryMapGridNode`: ``None`` for leaf nodes, a list of 4
        #: child nodes otherwise.
        self.children = None

        #: An attribute of :class:`NodeContentTypes`: The content type in this
        #: node. Only leaf nodes have content, this is ``None`` for all other
        #: nodes.
        self.content = None  # type: _NodeContentType

        self._next_child = 0  # Used when building to track which branch to follow

    def __repr__(self):
        return '<%s center: %s size: %s content: %s>' % (
            self.__class__.__name__, self.center, self.size, self.content)

    def contains_point(self, x, y):
        """Test if the node contains the given x,y coordinates.

        Args:
            x (float): x coordinate for the point
            y (float): y coordinate for the point

        Returns:
            bool: True if the node contains the point, False otherwise.
        """
        half_size = self.size * 0.5
        dist_x = abs(self.center.x - x)
        dist_y = abs(self.center.y - y)
        return (dist_x <= half_size) and (dist_y <= half_size)

    def _get_node(self, x, y, assumed_in_bounds):
        if not assumed_in_bounds and not self.contains_point(x, y):
            # point is out of bounds
            return None

        if self.children is None:
            return self
        else:
            x_offset = 2 if x < self.center.x else 0
            y_offset = 1 if y < self.center.y else 0
            child_node = self.children[x_offset+y_offset]
            # child node is by definition in bounds / on boundary
            return child_node._get_node(x, y, True)

    def get_node(self, x, y):
        """Get the node at the given x,y coordinates.

        Args:
            x (float): x coordinate for the point
            y (float): y coordinate for the point

        Returns:
            :class:`NavMemoryMapGridNode`: The smallest node that includes the
            point. Will be ``None`` if the point is outside of the map.
        """
        return self._get_node(x, y, assumed_in_bounds=False)

    def get_content(self, x, y):
        """Get the node's content at the given x,y coordinates.

        Args:
            x (float): x coordinate for the point
            y (float): y coordinate for the point

        Returns:
            :class:`_NodeContentType`: The content included at that point.
            Will be :attr:`NodeContentTypes.Unknown` if the point is outside of
            the map.
        """
        node = self.get_node(x, y)
        if node:
            return node.content
        else:
            return NodeContentTypes.Unknown

    def _add_child(self, content, depth):
        """Add a child node to the quad tree.

        The quad-tree is serialized to a flat list of nodes, we deserialize
        back to a quad-tree structure here, with the depth of each node
        indicating where it is placed.

        Args:
            content (:class:`_NodeContentType`): The content to store in the leaf node
            depth (int): The depth that this leaf node is located at.

        Returns:
            bool: True if parent should use the next child for future _add_child
            calls (this is an internal implementation detail of h
        """
        if depth > self.depth:
            logger.error("NavMemoryMapGridNode depth %s > %s", depth, self.depth)
        if self._next_child > 3:
            logger.error("NavMemoryMapGridNode _next_child %s (>3) at depth %s", self._next_child, self.depth)

        if self.depth == depth:
            if self.content is not None:
                logger.error("NavMemoryMapGridNode: Clobbering %s at depth %s with %s",
                             self.content, self.depth, content)
            self.content = content
            # This node won't be further subdivided, and is now full
            return True

        if self.children is None:
            # Create 4 child nodes for quad-tree structure
            next_depth = self.depth - 1
            next_size = self.size * 0.5
            offset = next_size * 0.5
            center1 = util.Vector3(self.center.x + offset, self.center.y + offset, self.center.z)
            center2 = util.Vector3(self.center.x + offset, self.center.y - offset, self.center.z)
            center3 = util.Vector3(self.center.x - offset, self.center.y + offset, self.center.z)
            center4 = util.Vector3(self.center.x - offset, self.center.y - offset, self.center.z)
            self.children = [NavMemoryMapGridNode(next_depth, next_size, center1, self),
                             NavMemoryMapGridNode(next_depth, next_size, center2, self),
                             NavMemoryMapGridNode(next_depth, next_size, center3, self),
                             NavMemoryMapGridNode(next_depth, next_size, center4, self)]
        if self.children[self._next_child]._add_child(content, depth):
            # Child node is now full, start using the next child
            self._next_child += 1

        if self._next_child > 3:
            # All children are now full - parent should start using the next child
            return True
        else:
            # Empty children remain - parent can keep using this child
            return False


class NavMemoryMapGrid:
    """A navigation memory map, stored as a quad-tree."""
    def __init__(self, origin_id, root_depth, root_size, root_center_x, root_center_y):
        #: int: The origin ID for the map. Only maps and :class:`~cozmo.util.Pose`
        #: objects of the same origin ID are in the same coordinate frame and
        #: can therefore be compared.
        self.origin_id = origin_id
        root_center = util.Vector3(root_center_x, root_center_y, 0.0)
        self._root_node = NavMemoryMapGridNode(root_depth, root_size, root_center, None)

    def __repr__(self):
        return '<%s center: %s size: %s>' % (
            self.__class__.__name__, self.center, self.size)

    @property
    def root_node(self):
        """:class:`NavMemoryMapGridNode`: The root node for the grid, contains all other nodes."""
        return self._root_node

    @property
    def size(self):
        """float: The size (width or length) of the square grid."""
        return self._root_node.size

    @property
    def center(self):
        """:class:`~cozmo.util.Vector3`: The center of this map."""
        return self._root_node.center

    def contains_point(self, x, y):
        """Test if the map contains the given x,y coordinates.

        Args:
            x (float): x coordinate for the point
            y (float): y coordinate for the point

        Returns:
            bool: True if the map contains the point, False otherwise.
        """
        return self._root_node.contains_point(x,y)

    def get_node(self, x, y):
        """Get the node at the given x,y coordinates.

        Args:
            x (float): x coordinate for the point
            y (float): y coordinate for the point

        Returns:
            :class:`NavMemoryMapGridNode`: The smallest node that includes the
            point. Will be ``None`` if the point is outside of the map.
        """
        return self._root_node.get_node(x, y)

    def get_content(self, x, y):
        """Get the map's content at the given x,y coordinates.

        Args:
            x (float): x coordinate for the point
            y (float): y coordinate for the point

        Returns:
            :class:`_NodeContentType`: The content included at that point.
            Will be :attr:`NodeContentTypes.Unknown` if the point is outside of
            the map.
        """
        return self._root_node.get_content(x, y)

    def _add_quad(self, content, depth):
        # Convert content int to our enum representation
        content = NodeContentTypes.find_by_id(content)
        self._root_node._add_child(content, depth)
