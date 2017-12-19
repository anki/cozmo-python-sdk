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
           'FACIAL_EXPRESSION_UNKNOWN', 'FACIAL_EXPRESSION_NEUTRAL', 'FACIAL_EXPRESSION_HAPPY',
           'FACIAL_EXPRESSION_SURPRISED', 'FACIAL_EXPRESSION_ANGRY', 'FACIAL_EXPRESSION_SAD',
           'EvtErasedEnrolledFace', 'EvtFaceAppeared', 'EvtFaceDisappeared',
           'EvtFaceIdChanged', 'EvtFaceObserved', 'EvtFaceRenamed',
           'Face',
           'erase_all_enrolled_faces', 'erase_enrolled_face_by_id',
           'update_enrolled_face_by_id']



from . import logger

from . import behavior
from . import event
from . import objects
from . import util

from ._clad import _clad_to_engine_iface
from ._clad import _clad_to_game_anki


#: Length of time in seconds to go without receiving an observed event before
#: assuming that Cozmo can no longer see a face.
FACE_VISIBILITY_TIMEOUT = objects.OBJECT_VISIBILITY_TIMEOUT

# Facial expressions that Cozmo can distinguish
#: Facial expression not recognized.
#: Call :func:`cozmo.robot.Robot.enable_facial_expression_estimation` to enable recognition.
FACIAL_EXPRESSION_UNKNOWN = "unknown"
#: Facial expression neutral
FACIAL_EXPRESSION_NEUTRAL = "neutral"
#: Facial expression happy
FACIAL_EXPRESSION_HAPPY = "happy"
#: Facial expression surprised
FACIAL_EXPRESSION_SURPRISED = "surprised"
#: Facial expression angry
FACIAL_EXPRESSION_ANGRY = "angry"
#: Facial expression sad
FACIAL_EXPRESSION_SAD = "sad"


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
    FACE_VISIBILITY_TIMEOUT seconds and then is seen again, a
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


def _clad_facial_expression_to_facial_expression(clad_expression_type):
    if clad_expression_type == _clad_to_game_anki.Vision.FacialExpression.Unknown:
        return FACIAL_EXPRESSION_UNKNOWN
    elif clad_expression_type == _clad_to_game_anki.Vision.FacialExpression.Neutral:
        return FACIAL_EXPRESSION_NEUTRAL
    elif clad_expression_type == _clad_to_game_anki.Vision.FacialExpression.Happiness:
        return FACIAL_EXPRESSION_HAPPY
    elif clad_expression_type == _clad_to_game_anki.Vision.FacialExpression.Surprise:
        return FACIAL_EXPRESSION_SURPRISED
    elif clad_expression_type == _clad_to_game_anki.Vision.FacialExpression.Anger:
        return FACIAL_EXPRESSION_ANGRY
    elif clad_expression_type == _clad_to_game_anki.Vision.FacialExpression.Sadness:
        return FACIAL_EXPRESSION_SAD
    else:
        raise ValueError("Unexpected facial expression type %s" % clad_expression_type)


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

    def __init__(self, conn, world, robot, face_id=None, **kw):
        super().__init__(conn, world, robot, **kw)
        self._face_id = face_id
        self._updated_face_id = None
        self._name = ''
        self._expression = None
        self._expression_score = None
        self._left_eye = None
        self._right_eye = None
        self._nose = None
        self._mouth = None

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

    @property
    def expression(self):
        '''string: The facial expression Cozmo has recognized on the face.

        Will be :attr:`FACIAL_EXPRESSION_UNKNOWN` by default if you haven't called
        :meth:`cozmo.robot.Robot.enable_facial_expression_estimation` to enable
        the facial expression estimation. Otherwise it will be equal to one of:
        :attr:`FACIAL_EXPRESSION_NEUTRAL`, :attr:`FACIAL_EXPRESSION_HAPPY`,
        :attr:`FACIAL_EXPRESSION_SURPRISED`, :attr:`FACIAL_EXPRESSION_ANGRY`,
        or :attr:`FACIAL_EXPRESSION_SAD`.
        '''
        return self._expression

    @property
    def expression_score(self):
        '''int: The score/confidence that :attr:`expression` was correct.

        Will be 0 if expression is :attr:`FACIAL_EXPRESSION_UNKNOWN` (e.g. if
        :meth:`cozmo.robot.Robot.enable_facial_expression_estimation` wasn't
        called yet). The maximum possible score is 100.
        '''
        return self._expression_score

    @property
    def known_expression(self):
        '''string: The known facial expression Cozmo has recognized on the face.

        Like :meth:`expression` but returns an empty string for the unknown expression.
        '''
        expression = self.expression
        if expression == FACIAL_EXPRESSION_UNKNOWN:
            return ""
        return expression

    @property
    def left_eye(self):
        '''sequence of tuples of float (x,y): points representing the outline of the left eye'''
        return self._left_eye

    @property
    def right_eye(self):
        '''sequence of tuples of float (x,y): points representing the outline of the right eye'''
        return self._right_eye

    @property
    def nose(self):
        '''sequence of tuples of float (x,y): points representing the outline of the nose'''
        return self._nose

    @property
    def mouth(self):
        '''sequence of tuples of float (x,y): points representing the outline of the mouth'''
        return self._mouth

    #### Private Event Handlers ####

    def _recv_msg_robot_observed_face(self, evt, *, msg):

        changed_fields = {'pose', 'left_eye', 'right_eye', 'nose', 'mouth'}
        self._pose = util.Pose._create_from_clad(msg.pose)
        self._name = msg.name

        expression = _clad_facial_expression_to_facial_expression(msg.expression)
        expression_score = 0

        if expression != FACIAL_EXPRESSION_UNKNOWN:
            expression_score = msg.expressionValues[msg.expression]
            if expression_score == 0:
                # The expression should have been marked unknown - this is a
                # bug in the engine because even a zero score overwrites the
                # default negative score for Unknown.
                expression = FACIAL_EXPRESSION_UNKNOWN

        if expression != self._expression:
            self._expression = expression
            changed_fields.add('expression')

        if expression_score != self._expression_score:
            self._expression_score = expression_score
            changed_fields.add('expression_score')

        self._left_eye = msg.leftEye
        self._right_eye = msg.rightEye
        self._nose = msg.nose
        self._mouth = msg.mouth

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

    def _is_valid_name(self, name):
        if not (name and name.isalpha()):
            return False
        try:
            name.encode('ascii')
        except UnicodeEncodeError:
            return False

        return True

    def name_face(self, name):
        '''Assign a name to this face. Cozmo will remember this name between SDK runs.

        Args:
            name (string): The name that will be assigned to this face. Must
                be a non-empty ASCII string of alphabetic characters only.
        Returns:
            An instance of :class:`cozmo.behavior.Behavior` object
        Raises:
            :class:`ValueError` if name is invalid.
        '''
        if not self._is_valid_name(name):
            raise ValueError("new_name '%s' is an invalid face name. "
                             "Must be non-empty and contain only alphabetic ASCII characters." % name)

        logger.info("Enrolling face=%s with name='%s'", self, name)

        # Note: saveID must be 0 if face_id doesn't already have a name
        msg = _clad_to_engine_iface.SetFaceToEnroll(name=name,
                                                    observedID=self.face_id,
                                                    saveID=0,
                                                    saveToRobot=True,
                                                    sayName=False,
                                                    useMusic=False)
        self.conn.send_msg(msg)

        enroll_behavior = self._robot.start_behavior(behavior.BehaviorTypes._EnrollFace)
        return enroll_behavior

    def rename_face(self, new_name):
        '''Change the name assigned to the face. Cozmo will remember this name between SDK runs.

        Args:
            new_name (string): The new name that will be assigned to this face. Must
                be a non-empty ASCII string of alphabetic characters only.
        Raises:
            :class:`ValueError` if new_name is invalid.
        '''
        if not self._is_valid_name(new_name):
            raise ValueError("new_name '%s' is an invalid face name. "
                             "Must be non-empty and contain only alphabetic ASCII characters." % new_name)
        update_enrolled_face_by_id(self.conn, self.face_id, self.name, new_name)

    def erase_enrolled_face(self):
        '''Remove the name associated with this face.

        Cozmo will no longer remember the name associated with this face between SDK runs.
        '''
        erase_enrolled_face_by_id(self.conn, self.face_id)


