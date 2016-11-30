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

'''Pet recognition.

Cozmo is capable of detecting pet faces (cats and dogs).

The :class:`cozmo.world.World` object keeps track of pets the robot currently
knows about, along with those that are currently visible to the camera.

Each pet is assigned a :class:`Pet` object, which generates a number of
observable events whenever the pet is observed, etc.

If a pet goes off-screen, it will be assigned a new object_id (and
therefore Pet object) when it returns. This is because the system can
only tell if something appears to be a cat or a dog; it cannot recognise
a specific pet, or e.g. tell the difference between two dogs.

Note that these pet-specific events are also passed up to the
:class:`cozmo.world.World` object, so events for all known pets can be
observed by adding handlers there.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['PET_VISIBILITY_TIMEOUT', 'PET_TYPE_UNKOWN', 'PET_TYPE_CAT', 'PET_TYPE_DOG',
           'EvtPetAppeared', 'EvtPetDisappeared', 'EvtPetObserved',
           'Pet']


import math
import time

from . import logger

from . import event
from . import objects
from . import util

from ._clad import _clad_to_game_anki


#: Length of time to go without receiving an observed event before
#: assuming that Cozmo can no longer see a pet.
PET_VISIBILITY_TIMEOUT = objects.OBJECT_VISIBILITY_TIMEOUT

# Pet types that Cozmo can distinguish
#: Pet Type reported by Cozmo when unsure of type of pet
PET_TYPE_UNKOWN = "Unknown"
#: Pet Type reported by Cozmo when he thinks it's a cat
PET_TYPE_CAT = "Cat"
#: Pet Type reported by Cozmo when he thinks it's a dog
PET_TYPE_DOG = "Dog"


class EvtPetObserved(event.Event):
    '''Triggered whenever a pet is visually identified by the robot.

    A stream of these events are produced while a pet is visible to the robot.
    Each event has an updated image_box field.

    See EvtPetAppeared if you only want to know when a pet first
    becomes visible.
    '''
    pet = 'The Pet instance that was observed'
    updated = 'A set of field names that have changed'
    image_box = 'A comzo.util.ImageBox defining where the pet is within Cozmo\'s camera view'


class EvtPetAppeared(event.Event):
    '''Triggered whenever an object is first visually identified by a robot.

    This differs from Evt{etObserved in that it's only triggered when
    a pet initially becomes visible.  If it disappears for more than
    PET_VISIBILITY_TIMEOUT (0.2) seconds and then is seen again, a
    EvtPetDisappeared will be dispatched, followed by another
    EvtPetAppeared event.

    For continuous tracking information about a visible pet, see
    EvtPetObserved.
    '''
    pet = 'The Pet instance that was observed'
    updated = 'A set of field names that have changed'
    image_box = 'A comzo.util.ImageBox defining where the pet is within Cozmo\'s camera view'


class EvtPetDisappeared(event.Event):
    '''Triggered whenever a pet that was previously being observed is no longer visible.'''
    pet = 'The Pet instance that is no longer being observed'


def _clad_pet_type_to_pet_type(clad_pet_type):
    if clad_pet_type == _clad_to_game_anki.Vision.PetType.Unknown:
        return PET_TYPE_UNKOWN
    elif clad_pet_type == _clad_to_game_anki.Vision.PetType.Cat:
        return PET_TYPE_CAT
    elif clad_pet_type == _clad_to_game_anki.Vision.PetType.Dog:
        return PET_TYPE_DOG
    else:
        raise ValueError("Unexpected pet type %s" % clad_pet_type)


class Pet(event.Dispatcher):
    '''A single pet (face) that Cozmo has detected.
    '''

    def __init__(self, conn, world, robot, pet_id=None, **kw):
        super().__init__(**kw)
        self._pet_id = pet_id
        self._robot = robot
        self._name = ''
        self._pose = None
        self.conn = conn
        #: :class:`cozmo.world.World`: instance in which this pet is located.
        self.world = world

        #: The type of Pet (PET_TYPE_CAT, PET_TYPE_DOG or PET_TYPE_UNKNOWN)
        self.pet_type = None

        #: float: The time the event was received.
        #: ``None`` if no events have yet been received.
        self.last_event_time = None

        #: float: The time the pet was last observed by the robot.
        #: ``None`` if the pet has not yet been observed.
        self.last_observed_time = None

        #: int: The robot's timestamp of the last observed event.
        #: ``None`` if the pet has not yet been observed.
        #: In milliseconds relative to robot epoch.
        self.last_observed_robot_timestamp = None

        #: :class:`~cozmo.util.ImageBox`: The ImageBox defining where the
        #: object was last visible within Cozmo's camera view.
        #: ``None`` if the pet has not yet been observed.
        self.last_observed_image_box = None

        self._is_visible = False
        self._observed_timeout_handler = None

    def __repr__(self):
        return '<%s pet_id=%s is_visible=%s pet_type=%s>' % (
            self.__class__.__name__, self.pet_id, self.is_visible, self.pet_type)

    #### Private Methods ####

    def _update_field(self, changed, field_name, new_value):
        # Set only changed fields and update the passed in changed set
        current = getattr(self, field_name)
        if current != new_value:
            setattr(self, field_name, new_value)
            changed.add(field_name)

    def _reset_observed_timeout_handler(self):
        if self._observed_timeout_handler is not None:
            self._observed_timeout_handler.cancel()
        self._observed_timeout_handler = self._loop.call_later(
                PET_VISIBILITY_TIMEOUT, self._observed_timeout)

    def _observed_timeout(self):
        # triggered when the object is no longer considered "visible"
        # ie. PET_VISIBILITY_TIMEOUT seconds after the last
        # object observed event
        self._is_visible = False
        self.dispatch_event(EvtPetDisappeared, pet=self)


    #### Properties ####

    @property
    def pet_id(self):
        '''int: The internal ID assigned to the pet.

        This value can only be assigned once as it is static in the engine.
        '''
        return self._pet_id

    @pet_id.setter
    def pet_id(self, value):
        if self._pet_id is not None:
            raise ValueError("Cannot change pet ID once set (from %s to %s)" % (self._pet_id, value))
        logger.debug("Updated pet_id for %s from %s to %s", self.__class__, self._pet_id, value)
        self._pet_id = value

    #### Private Event Handlers ####

    def _recv_msg_robot_observed_pet(self, evt, *, msg):
        changed_fields = {'last_observed_time', 'last_observed_robot_timestamp',
                'last_event_time', 'last_observed_image_box'}
        newly_visible = self._is_visible == False
        self._is_visible = True

        pet_type = _clad_pet_type_to_pet_type(msg.petType)
        if pet_type != self.pet_type:
            self.pet_type = pet_type
            changed_fields.add('pet_type')

        self.last_observed_time = time.time()
        self.last_observed_robot_timestamp = msg.timestamp
        self.last_event_time = time.time()

        image_box = util.ImageBox(msg.img_rect.x_topLeft, msg.img_rect.y_topLeft, msg.img_rect.width, msg.img_rect.height)
        self.last_observed_image_box = image_box

        self._reset_observed_timeout_handler()

        self.dispatch_event(EvtPetObserved, pet=self,
                updated=changed_fields, image_box=image_box)

        if newly_visible:
            self.dispatch_event(EvtPetAppeared, pet=self,
                    updated=changed_fields, image_box=image_box)

    #### Public Event Handlers ####

    #### Event Wrappers ####

    #### Commands ####

    @property
    def time_since_last_seen(self):
        '''float: time since this pet was last seen (math.inf if never)'''
        if self.last_observed_time is None:
            return math.inf
        return time.time() - self.last_observed_time

    @property
    def time_since_last_seen(self):
        '''float: time since this pet was last seen (math.inf if never)'''
        if self.last_observed_time is None:
            return math.inf
        return time.time() - self.last_observed_time

    @property
    def is_visible(self):
        '''bool: True if the pet has been observed recently.

        "recently" is defined as :const:`PET_VISIBILITY_TIMEOUT` seconds.
        '''
        return self._is_visible
