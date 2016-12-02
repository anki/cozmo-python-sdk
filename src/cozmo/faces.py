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

'''Face recognition and enrollment.

Cozmo is capable of recognizing human faces, tracking their position and rotation
("pose") and assigning names to them via an enrollment process.

The :class:`cozmo.world.World` object keeps track of faces the robot currently
knows about, along with those that are currently visible to the camera.

Each face is assigned a :class:`Face` object, which generates a number of
observable events whenever the face is observed, has its ID updated, is
renamed, etc.

Note that these face-specific events are also passed up to the
:class:`cozmo.world.World` object, so events for all known faces can be
observed by adding handlers there.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['FACE_VISIBILITY_TIMEOUT',
           'EvtErasedEnrolledFace', 'EvtFaceAppeared', 'EvtFaceDisappeared',
           'EvtFaceIdChanged', 'EvtFaceObserved', 'EvtFaceRenamed',
           'EnrollNamedFace', 'Face',
           'erase_all_enrolled_faces', 'erase_enrolled_face_by_id',
           'update_enrolled_face_by_id']


import math
import time

from . import logger

from . import action
from . import event
from . import objects
from . import util

from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo


#: Length of time to go without receiving an observed event before
#: assuming that Cozmo can no longer see a face.
FACE_VISIBILITY_TIMEOUT = objects.OBJECT_VISIBILITY_TIMEOUT


class EvtErasedEnrolledFace(event.Event):
    '''Triggered when a face enrollment is removed (via erase_enrolled_face_by_id)'''
    face = 'The Face instance that the enrollment is being erased for'
    old_name = 'The name previously used for this face'


class EvtFaceIdChanged(event.Event):
    '''Triggered whenever a face has its ID updated in engine.

    Generally occurs when:
    1) A tracked but unrecognized face (negative ID) is recognized and receives a positive ID or
    2) Face records get merged (on realization that 2 faces are actually the same)
    '''
    face = 'The Face instance that is being given a new id'
    old_id = 'The ID previously used for this face'
    new_id = 'The new ID that will be used for this face'


class EvtFaceObserved(event.Event):
    '''Triggered whenever a face is visually identified by the robot.

    A stream of these events are produced while a face is visible to the robot.
    Each event has an updated image_box field.

    See EvtFaceAppeared if you only want to know when a face first
    becomes visible.
    '''
    face = 'The Face instance that was observed'
    updated = 'A set of field names that have changed'
    image_box = 'A comzo.util.ImageBox defining where the face is within Cozmo\'s camera view'
    name = 'The name associated with the face that was observed'
    pose = 'The cozmo.util.Pose defining the position and rotation of the face.'


class EvtFaceAppeared(event.Event):
    '''Triggered whenever a face is first visually identified by a robot.

    This differs from EvtFaceObserved in that it's only triggered when
    a face initially becomes visible.  If it disappears for more than
    FACE_VISIBILITY_TIMEOUT (0.2) seconds and then is seen again, a
    EvtFaceDisappeared will be dispatched, followed by another
    EvtFaceAppeared event.

    For continuous tracking information about a visible face, see
    EvtFaceObserved.
    '''
    face = 'The Face instance that was observed'
    updated = 'A set of field names that have changed'
    image_box = 'A comzo.util.ImageBox defining where the face is within Cozmo\'s camera view'
    name = 'The name associated with the face that was observed'
    pose = 'The cozmo.util.Pose defining the position and rotation of the face.'


class EvtFaceDisappeared(event.Event):
    '''Triggered whenever a face that was previously being observed is no longer visible.'''
    face = 'The Face instance that is no longer being observed'


class EvtFaceRenamed(event.Event):
    '''Triggered whenever a face is renamed (via RobotRenamedEnrolledFace)'''
    face = 'The Face instance that is being given a new name'
    old_name = 'The name previously used for this face'
    new_name = 'The new name that will be used for this face'


def erase_all_enrolled_faces(conn):
    '''Erase the enrollment (name) records for all faces.

    Args:
        conn (:class:`~cozmo.conn.CozmoConnection`): The connection to send the message over
    '''
    msg = _clad_to_engine_iface.EraseAllEnrolledFaces()
    conn.send_msg(msg)


def erase_enrolled_face_by_id(conn, face_id):
    '''Erase the enrollment (name) record for the face with this ID.

    Args:
        conn (:class:`~cozmo.conn.CozmoConnection`): The connection to send the message over
        face_id (int): The ID of the face to erase.
    '''
    msg = _clad_to_engine_iface.EraseEnrolledFaceByID(face_id)
    conn.send_msg(msg)


def update_enrolled_face_by_id(conn, face_id, old_name, new_name):
    '''Update the name enrolled for a given face.

    Args:
        conn (:class:`~cozmo.conn.CozmoConnection`): The connection to send the message over.
        face_id (int): The ID of the face to rename.
        old_name (string): The old name of the face (must be correct, otherwise message is ignored).
        new_name (string): The new name for the face.
    '''
    msg = _clad_to_engine_iface.UpdateEnrolledFaceByID(face_id, old_name, new_name)
    conn.send_msg(msg)


class EnrollNamedFace(action.Action):
    '''Represents the enroll named face action in progress.

    Returned by :meth:`cozmo.faces.Face.name_face`
    '''

    _action_type = _clad_to_engine_cozmo.RobotActionType.ENROLL_NAMED_FACE

    def __init__(self, face, name, **kw):
        super().__init__(**kw)
        #: The face (e.g. an instance of :class:`cozmo.faces.Face`) that will be named.
        self.face = face
        #: The name that is going to be bound to the face.
        self.name = name

    def _repr_values(self):
        return "face=%s name=%s" % (self.face, self.name)

    def _encode(self):
        return _clad_to_engine_iface.EnrollNamedFace(faceID=self.face.face_id,
                                                     name=self.name,
                                                     sequence=_clad_to_engine_cozmo.FaceEnrollmentSequence.Simple)


class Face(objects.ObservableElement):
    '''A single face that Cozmo has detected.

    May represent a face that has previously been enrolled, in which case
    :attr:`name` will hold the name that it was enrolled with.

    Each Face instance has a :attr:`face_id` integer - This may change if
    Cozmo later gets an improved view and makes a different prediction about
    which face it is looking at.

    See parent class :class:`~cozmo.objects.ObservableElement` for additional properties
    and methods.
    '''

    #: Length of time in seconds to go without receiving an observed event before
    #: assuming that Cozmo can no longer see a face.
    visibility_timeout = FACE_VISIBILITY_TIMEOUT

    #: callable: The factory function to return an :class:`EnrollNamedFace`
    #: class or subclass instance.
    enroll_named_face_factory = EnrollNamedFace

    def __init__(self, conn, world, robot, face_id=None, **kw):
        super().__init__(conn, world, robot, **kw)
        self._face_id = face_id
        self._updated_face_id = None
        self._name = ''

    def _repr_values(self):
        return 'face_id=%s,%s name=%s' % (self.face_id, self.updated_face_id,
                                          self.name)

    #### Private Methods ####

    def _dispatch_observed_event(self, changed_fields, image_box):
        self.dispatch_event(EvtFaceObserved, face=self, name=self._name,
                updated=changed_fields, image_box=image_box, pose=self._pose)

    def _dispatch_appeared_event(self, changed_fields, image_box):
        self.dispatch_event(EvtFaceAppeared, face=self,
                updated=changed_fields, image_box=image_box, pose=self._pose)

    def _dispatch_disappeared_event(self):
        self.dispatch_event(EvtFaceDisappeared, face=self)

    #### Properties ####

    @property
    def face_id(self):
        '''int: The internal ID assigned to the face.

        This value can only be assigned once as it is static in the engine.
        '''
        return self._face_id

    @face_id.setter
    def face_id(self, value):
        if self._face_id is not None:
            raise ValueError("Cannot change face ID once set (from %s to %s)" % (self._face_id, value))
        logger.debug("Updated face_id for %s from %s to %s", self.__class__, self._face_id, value)
        self._face_id = value

    @property
    def has_updated_face_id(self):
        '''bool: True if this face been updated / superseded by a face with a new ID'''
        return self._updated_face_id is not None

    @property
    def updated_face_id(self):
        '''int: The ID for the face that superseded this one (if any, otherwise :meth:`face_id`)'''
        if self.has_updated_face_id:
            return self._updated_face_id
        else:
            return self.face_id

    @property
    def name(self):
        '''string: The name Cozmo has associated with the face in his memory.

        This string will be empty if the face is not recognized or enrolled.
        '''
        return self._name

    #### Private Event Handlers ####

    def _recv_msg_robot_observed_face(self, evt, *, msg):

        changed_fields = {'pose'}
        self._pose = util.Pose._create_from_clad(msg.pose)
        self._name = msg.name

        image_box = util.ImageBox._create_from_clad_rect(msg.img_rect)
        self._on_observed(image_box, msg.timestamp, changed_fields)

    def _recv_msg_robot_changed_observed_face_id(self, evt, *, msg):
        self._updated_face_id = msg.newID
        self.dispatch_event(EvtFaceIdChanged, face=self, old_id=msg.oldID, new_id = msg.newID)

    def _recv_msg_robot_renamed_enrolled_face(self, evt, *, msg):
        old_name = self._name
        self._name = msg.name
        self.dispatch_event(EvtFaceRenamed, face=self, old_name=old_name, new_name=msg.name)

    def _recv_msg_robot_erased_enrolled_face(self, evt, *, msg):
        old_name = self._name
        self._name = ''
        self.dispatch_event(EvtErasedEnrolledFace, face=self, old_name=old_name)

    #### Public Event Handlers ####

    #### Event Wrappers ####

    #### Commands ####

    def name_face(self, name):
        '''Assign a name to this face. Cozmo will remember this name between SDK runs.

        Args:
            name (string): The name that will be assigned to this face
        Returns:
            An instance of :class:`cozmo.faces.EnrollNamedFace` action object
        '''
        logger.info("Sending enroll named face request for face=%s and name=%s", self, name)
        action = self.enroll_named_face_factory(face=self, name=name, conn=self.conn,
                                                robot=self._robot, dispatch_parent=self)
        self._robot._action_dispatcher._send_single_action(action)
        return action

    def rename_face(self, new_name):
        '''Change the name assigned to the face. Cozmo will remember this name between SDK runs.

        Args:
            new_name (string): The new name for the face
        '''
        update_enrolled_face_by_id(self.conn, self.face_id, self.name, new_name)

    def erase_enrolled_face(self):
        '''Remove the name associated with this face.

        Cozmo will no longer remember the name associated with this face between SDK runs.
        '''
        erase_enrolled_face_by_id(self.conn, self.face_id)


