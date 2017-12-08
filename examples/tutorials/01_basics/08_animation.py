#!/usr/bin/env python3

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

'''Play some animations on Cozmo

Play an animation using a trigger, and then another animation by name.
'''

import cozmo


def cozmo_program(robot: cozmo.robot.Robot):
    # Play an animation via a Trigger - see:
    # http://cozmosdk.anki.com/docs/generated/cozmo.anim.html#cozmo.anim.Triggers
    # for a list of available triggers.
    # A trigger can pick from several appropriate animations for variety.
    print("Playing Animation Trigger 1:")
    robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceLoseSession).wait_for_completed()

    # Play the same trigger, but this time ignore the track that plays on the
    # body (i.e. don't move the wheels). See the play_anim_trigger documentation
    # for other available settings.
    print("Playing Animation Trigger 2: (Ignoring the body track)")
    robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceLoseSession, ignore_body_track=True).wait_for_completed()

    # Play an animation via its Name.
    # Warning: Future versions of the app might change these, so for future-proofing
    # we recommend using play_anim_trigger above instead.
    # See the remote_control_cozmo.py example in apps for an easy way to see
    # the available animations.
    print("Playing Animation 3:")
    robot.play_anim(name="anim_poked_giggle").wait_for_completed()


cozmo.run_program(cozmo_program)
