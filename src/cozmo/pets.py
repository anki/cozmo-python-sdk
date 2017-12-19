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

'''Pet detection.

Cozmo is capable of detecting pet faces (cats and dogs).

The :class:`cozmo.world.World` object keeps track of pets the robot currently
knows about, along with those that are currently visible to the camera.

Each pet is assigned a :class:`Pet` object, which generates a number of
observable events whenever the pet is observed, etc.

If a pet goes off-screen, it will be assigned a new object_id (and
therefore a new Pet object will be created) when it returns. 
This is because the system can only tell if something appears to be 
a cat or a dog; it cannot recognize a specific pet or, for instance, 
tell the difference between two dogs.

Note that these pet-specific events are also passed up to the
:class:`cozmo.world.World` object, so events for all pets can be
observed by adding handlers there.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['PET_VISIBILITY_TIMEOUT', 'PET_TYPE_CAT', 'PET_TYPE_DOG', 'PET_TYPE_UNKNOWN',
           'EvtPetAppeared', 'EvtPetDisappeared', 'EvtPetObserved',
           'Pet']


import math
import time

from . import logger

from . import event
from . import objects
from . import util

from ._clad import _clad_to_game_anki


#: Length of time in seconds to go without receiving an observed event before
#: assuming that Cozmo can no longer see a pet.
PET_VISIBILITY_TIMEOUT = objects.OBJECT_VISIBILITY_TIMEOUT

# Pet types that Cozmo can distinguish
#: Pet Type reported by Cozmo when unsure of type of pet
PET_TYPE_UNKNOWN = "unknown"
#: Pet Type reported by Cozmo when he thinks it's a cat
PET_TYPE_CAT = "cat"
#: Pet Type reported by Cozmo when he thinks it's a dog
PET_TYPE_DOG = "dog"


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
    '''Triggered whenever a pet is first visually identified by a robot.

    This differs from EvtPetObserved in that it's only triggered when
    a pet initially becomes visible.  If it disappears for more than
    PET_VISIBILITY_TIMEOUT seconds and then is seen again, a
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
        return PET_TYPE_UNKNOWN
    elif clad_pet_type == _clad_to_game_anki.Vision.PetType.Cat:
        return PET_TYPE_CAT
    elif clad_pet_type == _clad_to_game_anki.Vision.PetType.Dog:
        return PET_TYPE_DOG
    else:
        raise ValueError("Unexpected pet type %s" % clad_pet_type)


class Pet(objects.ObservableElement):
    '''A single pet that Cozmo has detected.

    See parent class :class:`~cozmo.objects.ObservableElement` for additional properties
    and methods.
    '''

    #: Length of time in seconds to go without receiving an observed event before
    #: assuming that Cozmo can no longer see a pet.
    visibility_timeout = PET_VISIBILITY_TIMEOUT

    def __init__(self, conn, world, robot, pet_id=None, **kw):
        super().__init__(conn, world, robot, **kw)
        self._pet_id = pet_id
        #: The type of Pet (PET_TYPE_CAT, PET_TYPE_DOG or PET_TYPE_UNKNOWN)
        self.pet_type = None

    def _repr_values(self):
        return 'pet_id=%s pet_type=%s' % (self.pet_id, self.pet_type)

    #### Private Methods ####

    def _dispatch_observed_event(self, changed_fields, image_box):
        self.dispatch_event(EvtPetObserved, pet=self,
                updated=changed_fields, image_box=image_box)

    def _dispatch_appeared_event(self, changed_fields, image_box):
        self.dispatch_event(EvtPetAppeared, pet=self,
                            updated=changed_fields, image_box=image_box)

    def _dispatch_disappeared_event(self):
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

        changed_fields = set()
        pet_type = _clad_pet_type_to_pet_type(msg.petType)
        if pet_type != self.pet_type:
            self.pet_type = pet_type
            changed_fields.add('pet_type')

        image_box = util.ImageBox._create_from_clad_rect(msg.img_rect)
        self._on_observed(image_box, msg.timestamp, changed_fields)

    #### Public Event Handlers ####

    #### Event Wrappers ####

    #### Commands ####
