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

'''
Audio related classes, functions, events and values.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['AudioEvents']

import collections

from . import logger

from . import action
from . import exceptions
from . import event

from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo, _clad_to_engine_anki, CladEnumWrapper


# generate names for each CLAD defined trigger

class _AudioEvent(collections.namedtuple('_AudioEvent', 'name id')):
    # Tuple mapping between CLAD AudioEvents name and ID
    # All instances will be members of AudioEvents

    # Keep _AudioEvent as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'AudioEvents.%s' % self.name


class AudioEvents(CladEnumWrapper):
    """The possible values for an AudioEvent.
    Pass one of these event objects to robot.play_audio() to play the corresponding sound clip.
    Example: ``robot.play_audio(cozmo.audio.AudioEvents.MusicFunLoop)``
    """
    _clad_enum = _clad_to_engine_anki.AudioMetaData.GameEvent.Codelab
    _entry_type = _AudioEvent

    #: Reserved Id for invalid sound events
    Invalid = _entry_type("Invalid", _clad_enum.Invalid)

    #: Stop all playing music
    MusicGlobalStop = _entry_type("MusicGlobalStop", _clad_enum.Music_Global_Stop)

    #: Mute cozmo background music
    MusicBackgroundSilenceOn = _entry_type("MusicBackgroundSilenceOn", _clad_enum.Music_Background_Silence_On)
    #: Unmute cozmo background music
    MusicBackgroundSilenceOff = _entry_type("MusicBackgroundSilenceOff", _clad_enum.Music_Background_Silence_Off)

    #: Initialize the synchronized tiny orchestra system
    #: (Will not produce any sound on its own, one of the modes must be triggered)
    MusicTinyOrchestraInit = _entry_type("MusicTinyOrchestraInit", _clad_enum.Music_Tiny_Orchestra_Init)
    #: Turn off the synchronized tiny orchestra system
    MusicTinyOrchestraStop = _entry_type("MusicTinyOrchestraStop", _clad_enum.Music_Tiny_Orchestra_Stop)

    #: Turn on the first mode of the synchronized tiny orchestra bass channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraBassMode1 = _entry_type("MusicTinyOrchestraBassMode1", _clad_enum.Music_Tiny_Orchestra_Bass_Mode_1)
    #: Turn off the first mode of the synchronized tiny orchestra bass channel
    MusicTinyOrchestraBassMode1Stop = _entry_type("MusicTinyOrchestraBassMode1Stop", _clad_enum.Music_Tiny_Orchestra_Bass_Mode_1_Stop)
    #: Turn on the second mode of the synchronized tiny orchestra bass channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraBassMode2 = _entry_type("MusicTinyOrchestraBassMode2", _clad_enum.Music_Tiny_Orchestra_Bass_Mode_2)
    #: Turn off the second mode of the synchronized tiny orchestra bass channel
    MusicTinyOrchestraBassMode2Stop = _entry_type("MusicTinyOrchestraBassMode2Stop", _clad_enum.Music_Tiny_Orchestra_Bass_Mode_2_Stop)
    #: Turn on the third mode of the synchronized tiny orchestra bass channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraBassMode3 = _entry_type("MusicTinyOrchestraBassMode3", _clad_enum.Music_Tiny_Orchestra_Bass_Mode_3)
    #: Turn off the third mode of the synchronized tiny orchestra bass channel
    MusicTinyOrchestraBassMode3Stop = _entry_type("MusicTinyOrchestraBassMode3Stop", _clad_enum.Music_Tiny_Orchestra_Bass_Mode_3_Stop)
    #: Turn off all synchronized tiny orchestra bass channels
    MusicTinyOrchestraBassStop = _entry_type("MusicTinyOrchestraBassStop", _clad_enum.Music_Tiny_Orchestra_Bass_Stop)

    #: Turn on the first mode of the synchronized tiny orchestra glock pluck channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraGlockPluckMode1 = _entry_type("MusicTinyOrchestraGlockPluckMode1", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_Mode_1)
    #: Turn off the first mode of the synchronized tiny orchestra glock pluck channel
    MusicTinyOrchestraGlockPluckMode1Stop = _entry_type("MusicTinyOrchestraGlockPluckMode1Stop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_Mode_1_Stop)
    #: Turn on the second mode of the synchronized tiny orchestra glock pluck channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraGlockPluckMode2 = _entry_type("MusicTinyOrchestraGlockPluckMode2", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_Mode_2)
    #: Turn off the second mode of the synchronized tiny orchestra glock pluck channel
    MusicTinyOrchestraGlockPluckMode2Stop = _entry_type("MusicTinyOrchestraGlockPluckMode2Stop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_Mode_2_Stop)
    #: Turn on the third mode of the synchronized tiny orchestra glock pluck channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraGlockPluckMode3 = _entry_type("MusicTinyOrchestraGlockPluckMode3", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_Mode_3)
    #: Turn off the third mode of the synchronized tiny orchestra glock pluck channel
    MusicTinyOrchestraGlockPluckMode3Stop = _entry_type("MusicTinyOrchestraGlockPluckMode3Stop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_Mode_3_Stop)
    #: Turn off all synchronized tiny orchestra glock pluck channels
    MusicTinyOrchestraGlockPluckStop = _entry_type("MusicTinyOrchestraGlockPluckStop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_Stop)

    #: Turn on the first mode of the synchronized tiny orchestra strings channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraStringsMode1 = _entry_type("MusicTinyOrchestraStringsMode1", _clad_enum.Music_Tiny_Orchestra_Strings_Mode_1)
    #: Turn off the first mode of the synchronized tiny orchestra strings channel
    MusicTinyOrchestraStringsMode1Stop = _entry_type("MusicTinyOrchestraStringsMode1Stop", _clad_enum.Music_Tiny_Orchestra_Strings_Mode_1_Stop)
    #: Turn on the second mode of the synchronized tiny orchestra strings channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraStringsMode2 = _entry_type("MusicTinyOrchestraStringsMode2", _clad_enum.Music_Tiny_Orchestra_Strings_Mode_2)
    #: Turn off the second mode of the synchronized tiny orchestra strings channel
    MusicTinyOrchestraStringsMode2Stop = _entry_type("MusicTinyOrchestraStringsMode2Stop", _clad_enum.Music_Tiny_Orchestra_Strings_Mode_2_Stop)
    #: Turn on the third mode of the synchronized tiny orchestra strings channel
    #: (Requires the tiny orchestra system be initialized, and will loop until the system is turned off)
    MusicTinyOrchestraStringsMode3 = _entry_type("MusicTinyOrchestraStringsMode3", _clad_enum.Music_Tiny_Orchestra_Strings_Mode_3)
    #: Turn off the third mode of the synchronized tiny orchestra strings channel
    MusicTinyOrchestraStringsMode3Stop = _entry_type("MusicTinyOrchestraStringsMode3Stop", _clad_enum.Music_Tiny_Orchestra_Strings_Mode_3_Stop)
    #: Turn off all synchronized tiny orchestra strings channels
    MusicTinyOrchestraStringsStop = _entry_type("MusicTinyOrchestraStringsStop", _clad_enum.Music_Tiny_Orchestra_Strings_Stop)

    #: Plays the first tiny orchestra bass track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraBass01Loop = _entry_type("MusicTinyOrchestraBass01Loop", _clad_enum.Music_Tiny_Orchestra_Bass_01_Loop)
    #: Stops active plays of the first tiny orchestra bass track
    MusicTinyOrchestraBass01LoopStop = _entry_type("MusicTinyOrchestraBass01LoopStop", _clad_enum.Music_Tiny_Orchestra_Bass_01_Loop_Stop)
    #: Plays the second tiny orchestra bass track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraBass02Loop = _entry_type("MusicTinyOrchestraBass02Loop", _clad_enum.Music_Tiny_Orchestra_Bass_02_Loop)
    #: Stops active plays of the second tiny orchestra bass track
    MusicTinyOrchestraBass02LoopStop = _entry_type("MusicTinyOrchestraBass02LoopStop", _clad_enum.Music_Tiny_Orchestra_Bass_02_Loop_Stop)
    #: Plays the third tiny orchestra bass track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraBass03Loop = _entry_type("MusicTinyOrchestraBass03Loop", _clad_enum.Music_Tiny_Orchestra_Bass_03_Loop)
    #: Stops active plays of the third tiny orchestra bass track
    MusicTinyOrchestraBass03LoopStop = _entry_type("MusicTinyOrchestraBass03LoopStop", _clad_enum.Music_Tiny_Orchestra_Bass_03_Loop_Stop)

    #: Plays the first tiny orchestra glock pluck track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraGlockPluck01Loop = _entry_type("MusicTinyOrchestraGlockPluck01Loop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_01_Loop)
    #: Stops active plays of the first tiny orchestra glock pluck track
    MusicTinyOrchestraGlockPluck01LoopStop = _entry_type("MusicTinyOrchestraGlockPluck01LoopStop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_01_Loop_Stop)
    #: Plays the second tiny orchestra glock pluck track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraGlockPluck02Loop = _entry_type("MusicTinyOrchestraGlockPluck02Loop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_02_Loop)
    #: Stops active plays of the second tiny orchestra glock pluck track
    MusicTinyOrchestraGlockPluck02LoopStop = _entry_type("MusicTinyOrchestraGlockPluck02LoopStop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_02_Loop_Stop)
    #: Plays the third tiny orchestra glock pluck track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraGlockPluck03Loop = _entry_type("MusicTinyOrchestraGlockPluck03Loop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_03_Loop)
    #: Stops active plays of the third tiny orchestra glock pluck track
    MusicTinyOrchestraGlockPluck03LoopStop = _entry_type("MusicTinyOrchestraGlockPluck03LoopStop", _clad_enum.Music_Tiny_Orchestra_Glock_Pluck_03_Loop_Stop)

    #: Plays the first tiny orchestra string track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraStrings01Loop = _entry_type("MusicTinyOrchestraStrings01Loop", _clad_enum.Music_Tiny_Orchestra_Strings_01_Loop)
    #: Stops active plays of the first tiny orchestra strings track
    MusicTinyOrchestraStrings01LoopStop = _entry_type("MusicTinyOrchestraStrings01LoopStop", _clad_enum.Music_Tiny_Orchestra_Strings_01_Loop_Stop)
    #: Plays the second tiny orchestra string track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraStrings02Loop = _entry_type("MusicTinyOrchestraStrings02Loop", _clad_enum.Music_Tiny_Orchestra_Strings_02_Loop)
    #: Stops active plays of the second tiny orchestra strings track
    MusicTinyOrchestraStrings02LoopStop = _entry_type("MusicTinyOrchestraStrings02LoopStop", _clad_enum.Music_Tiny_Orchestra_Strings_02_Loop_Stop)
    #: Plays the third tiny orchestra string track
    #: (Does not repeat. Does not interact with the synchronized tiny orchestra system)
    MusicTinyOrchestraStrings03Loop = _entry_type("MusicTinyOrchestraStrings03Loop", _clad_enum.Music_Tiny_Orchestra_Strings_03_Loop)
    #: Stops active plays of the third tiny orchestra strings track
    MusicTinyOrchestraStrings03LoopStop = _entry_type("MusicTinyOrchestraStrings03LoopStop", _clad_enum.Music_Tiny_Orchestra_Strings_03_Loop_Stop)

    #: Plays the cube whack music
    MusicCubeWhack = _entry_type("MusicCubeWhack", _clad_enum.Music_Cube_Whack)

    #: Plays the level 1 hot potato music
    #: (Does not repeat)
    MusicHotPotatoLevel1Loop = _entry_type("MusicHotPotatoLevel1Loop", _clad_enum.Music_Hot_Potato_Level_1_Loop)
    #: Stops active plays of the level 1 hot potato music
    MusicHotPotatoLevel1LoopStop = _entry_type("MusicHotPotatoLevel1LoopStop", _clad_enum.Music_Hot_Potato_Level_1_Loop_Stop)
    #: Plays the level 2 hot potato music
    #: (Does not repeat)
    MusicHotPotatoLevel2Loop = _entry_type("MusicHotPotatoLevel2Loop", _clad_enum.Music_Hot_Potato_Level_2_Loop)
    #: Stops active plays of the level 2 hot potato music
    MusicHotPotatoLevel2LoopStop = _entry_type("MusicHotPotatoLevel2LoopStop", _clad_enum.Music_Hot_Potato_Level_2_Loop_Stop)
    #: Plays the level 3 hot potato music
    #: (Does not repeat)
    MusicHotPotatoLevel3Loop = _entry_type("MusicHotPotatoLevel3Loop", _clad_enum.Music_Hot_Potato_Level_3_Loop)
    #: Stops active plays of the level 3 hot potato music
    MusicHotPotatoLevel3LoopStop = _entry_type("MusicHotPotatoLevel3LoopStop", _clad_enum.Music_Hot_Potato_Level_3_Loop_Stop)
    #: Plays the level 4 hot potato music
    #: (Does not repeat)
    MusicHotPotatoLevel4Loop = _entry_type("MusicHotPotatoLevel4Loop", _clad_enum.Music_Hot_Potato_Level_4_Loop)
    #: Stops active plays of the level 4 hot potato music
    MusicHotPotatoLevel4LoopStop = _entry_type("MusicHotPotatoLevel4LoopStop", _clad_enum.Music_Hot_Potato_Level_4_Loop_Stop)

    #: Plays the magic fortune teller reveal music
    MusicMagic8RevealStinger = _entry_type("MusicMagic8RevealStinger", _clad_enum.Music_Magic8_Reveal_Stinger)
    #: Stops active plays of the magic fortune teller reveal music
    MusicMagic8RevealStingerStop = _entry_type("MusicMagic8RevealStingerStop", _clad_enum.Music_Magic8_Reveal_Stinger_Stop)

    #: Plays 80s style music
    #: (Does not repeat)
    MusicStyle80S1159BpmLoop = _entry_type("MusicStyle80S1159BpmLoop", _clad_enum.Music_Style_80S_1_159Bpm_Loop)
    #: Stops active plays of 80s style music
    MusicStyle80S1159BpmLoopStop = _entry_type("MusicStyle80S1159BpmLoopStop", _clad_enum.Music_Style_80S_1_159Bpm_Loop_Stop)
    #: Plays disco style music
    #: (Does not repeat)
    MusicStyleDisco1135BpmLoop = _entry_type("MusicStyleDisco1135BpmLoop", _clad_enum.Music_Style_Disco_1_135Bpm_Loop)
    #: Stops active plays of disco style music
    MusicStyleDisco1135BpmLoopStop = _entry_type("MusicStyleDisco1135BpmLoopStop", _clad_enum.Music_Style_Disco_1_135Bpm_Loop_Stop)
    #: Plays mambo style music
    #: (Does not repeat)
    MusicStyleMambo1183BpmLoop = _entry_type("MusicStyleMambo1183BpmLoop", _clad_enum.Music_Style_Mambo_1_183Bpm_Loop)
    #: Stops active plays of mambo style music
    MusicStyleMambo1183BpmLoopStop = _entry_type("MusicStyleMambo1183BpmLoopStop", _clad_enum.Music_Style_Mambo_1_183Bpm_Loop_Stop)

    #: Stops all playing sound effects
    SfxGlobalStop = _entry_type("SfxGlobalStop", _clad_enum.Sfx_Global_Stop)

    #: Plays cube light sound
    SfxCubeLight = _entry_type("SfxCubeLight", _clad_enum.Sfx_Cube_Light)
    #: Stops active plays of cube light sound
    SfxCubeLightStop = _entry_type("SfxCubeLightStop", _clad_enum.Sfx_Cube_Light_Stop)

    #: Plays firetruck timer start sound
    SfxFiretruckTimerStart = _entry_type("SfxFiretruckTimerStart", _clad_enum.Sfx_Firetruck_Timer_Start)
    #: Stops active plays of firetruck timer start sound
    SfxFiretruckTimerStartStop = _entry_type("SfxFiretruckTimerStartStop", _clad_enum.Sfx_Firetruck_Timer_Start_Stop)
    #: Plays firetruck timer end sound
    SfxFiretruckTimerEnd = _entry_type("SfxFiretruckTimerEnd", _clad_enum.Sfx_Firetruck_Timer_End)
    #: Stops active plays of firetruck timer end sound
    SfxFiretruckTimerEndStop = _entry_type("SfxFiretruckTimerEndStop", _clad_enum.Sfx_Firetruck_Timer_End_Stop)

    #: Plays game win sound
    SfxGameWin = _entry_type("SfxGameWin", _clad_enum.Sfx_Game_Win)
    #: Stops active plays of game win sound
    SfxGameWinStop = _entry_type("SfxGameWinStop", _clad_enum.Sfx_Game_Win_Stop)
    #: Plays game lose sound
    SfxGameLose = _entry_type("SfxGameLose", _clad_enum.Sfx_Game_Lose)
    #: Stops active plays of game lose sound
    SfxGameLoseStop = _entry_type("SfxGameLoseStop", _clad_enum.Sfx_Game_Lose_Stop)

    #: Plays hot potato cube charge sound
    SfxHotPotatoCubeCharge = _entry_type("SfxHotPotatoCubeCharge", _clad_enum.Sfx_Hot_Potato_Cube_Charge)
    #: Stops active plays of hot potato cube charge sound
    SfxHotPotatoCubeChargeStop = _entry_type("SfxHotPotatoCubeChargeStop", _clad_enum.Sfx_Hot_Potato_Cube_Charge_Stop)
    #: Plays hot potato cube ready sound
    SfxHotPotatoCubeReady = _entry_type("SfxHotPotatoCubeReady", _clad_enum.Sfx_Hot_Potato_Cube_Ready)
    #: Stops active plays of hot potato cube ready sound
    SfxHotPotatoCubeReadyStop = _entry_type("SfxHotPotatoCubeReadyStop", _clad_enum.Sfx_Hot_Potato_Cube_Ready_Stop)
    #: Plays hot potato pass sound
    SfxHotPotatoPass = _entry_type("SfxHotPotatoPass", _clad_enum.Sfx_Hot_Potato_Pass)
    #: Stops active plays of hot potato pass sound
    SfxHotPotatoPassStop = _entry_type("SfxHotPotatoPassStop", _clad_enum.Sfx_Hot_Potato_Pass_Stop)
    #: Plays hot potato timer end sound
    SfxHotPotatoTimerEnd = _entry_type("SfxHotPotatoTimerEnd", _clad_enum.Sfx_Hot_Potato_Timer_End)
    #: Stops active plays of hot potato timer end sound
    SfxHotPotatoTimerEndStop = _entry_type("SfxHotPotatoTimerEndStop", _clad_enum.Sfx_Hot_Potato_Timer_End_Stop)

    #: Plays magic fortune teller message reveal sound
    SfxMagic8MessageReveal = _entry_type("SfxMagic8MessageReveal", _clad_enum.Sfx_Magic8_Message_Reveal)
    #: Stops active plays of magic fortune teller message reveal sound
    SfxMagic8MessageRevealStop = _entry_type("SfxMagic8MessageRevealStop", _clad_enum.Sfx_Magic8_Message_Reveal_Stop)

    #: Plays magnet attract sound
    SfxMagnetAttract = _entry_type("SfxMagnetAttract", _clad_enum.Sfx_Magnet_Attract)
    #: Stops active plays of magnet attrack sound
    SfxMagnetAttractStop = _entry_type("SfxMagnetAttractStop", _clad_enum.Sfx_Magnet_Attract_Stop)
    #: Plays magnet repel sound
    SfxMagnetRepel = _entry_type("SfxMagnetRepel", _clad_enum.Sfx_Magnet_Repel)
    #: Stops active plays of magnet repel sound
    SfxMagnetRepelStop = _entry_type("SfxMagnetRepelStop", _clad_enum.Sfx_Magnet_Repel_Stop)

    #: Plays countdown sound
    SfxSharedCountdown = _entry_type("SfxSharedCountdown", _clad_enum.Sfx_Shared_Countdown)
    #: Stops active plays of countdown sound
    SfxSharedCountdownStop = _entry_type("SfxSharedCountdownStop", _clad_enum.Sfx_Shared_Countdown_Stop)
    #: Plays cube light on sound
    SfxSharedCubeLightOn = _entry_type("SfxSharedCubeLightOn", _clad_enum.Sfx_Shared_Cube_Light_On)
    #: Stops active plays of cube light on sound
    SfxSharedCubeLightOnStop = _entry_type("SfxSharedCubeLightOnStop", _clad_enum.Sfx_Shared_Cube_Light_On_Stop)
    #: Plays error sound
    SfxSharedError = _entry_type("SfxSharedError", _clad_enum.Sfx_Shared_Error)
    #: Stops active plays of error sound
    SfxSharedErrorStop = _entry_type("SfxSharedErrorStop", _clad_enum.Sfx_Shared_Error_Stop)
    #: Plays success sound
    SfxSharedSuccess = _entry_type("SfxSharedSuccess", _clad_enum.Sfx_Shared_Success)
    #: Stops active plays of success sound
    SfxSharedSuccessStop = _entry_type("SfxSharedSuccessStop", _clad_enum.Sfx_Shared_Success_Stop)
    #: Plays timer click sound
    SfxSharedTimerClick = _entry_type("SfxSharedTimerClick", _clad_enum.Sfx_Shared_Timer_Click)
    #: Stops active plays of timer click sound
    SfxSharedTimerClickStop = _entry_type("SfxSharedTimerClickStop", _clad_enum.Sfx_Shared_Timer_Click_Stop)
    #: Plays timer end sound
    SfxSharedTimerEnd = _entry_type("SfxSharedTimerEnd", _clad_enum.Sfx_Shared_Timer_End)
    #: Stops active plays of timer end sound
    SfxSharedTimerEndStop = _entry_type("SfxSharedTimerEndStop", _clad_enum.Sfx_Shared_Timer_End_Stop)
    #: Plays timer warning sound
    SfxSharedTimerWarning = _entry_type("SfxSharedTimerWarning", _clad_enum.Sfx_Shared_Timer_Warning)
    #: Stop all active plays of timer warning sound
    SfxSharedTimerWarningStop = _entry_type("SfxSharedTimerWarningStop", _clad_enum.Sfx_Shared_Timer_Warning_Stop)

    #: Plays a fun music sound (that loops indefinitely).
    MusicFunLoop = _entry_type("Music_Fun_Loop", _clad_enum.Music_Fun_Loop)
    #: Stops all active plays of the fun music sound.
    MusicFunLoopStop = _entry_type("Music_Fun_Loop_Stop", _clad_enum.Music_Fun_Loop_Stop)

    #: Plays the putt-hole-success sound.
    SfxPuttHoleSuccess = _entry_type("Sfx_Putt_Hole_Success", _clad_enum.Sfx_Putt_Hole_Success)
    #: Stops all active plays of the putt-hole-success sound.
    SfxPuttHoleSuccessStop = _entry_type("Sfx_Putt_Hole_Success_Stop", _clad_enum.Sfx_Putt_Hole_Success_Stop)

    #: Plays alien invasion sound.
    Sfx_Alien_Invasion_Ufo = _entry_type("Sfx_Alien_Invasion_Ufo", _clad_enum.Sfx_Alien_Invasion_Ufo)
    #: Stops all active plays of the alien invasion sound.
    Sfx_Alien_Invasion_Ufo_Stop = _entry_type("Sfx_Alien_Invasion_Ufo_Stop", _clad_enum.Sfx_Alien_Invasion_Ufo_Stop)

    #: Plays brick bash sound.
    Sfx_Brick_Bash = _entry_type("Sfx_Brick_Bash", _clad_enum.Sfx_Brick_Bash)
    #: Stops all active plays of the brick bash sound.
    Sfx_Brick_Bash_Stop = _entry_type("Sfx_Brick_Bash_Stop", _clad_enum.Sfx_Brick_Bash_Stop)

    #: Plays constellation star sound.
    Sfx_Constellation_Star = _entry_type("Sfx_Constellation_Star", _clad_enum.Sfx_Constellation_Star)
    #: Stops all active plays of the constellation star sound.
    Sfx_Constellation_Star_Stop = _entry_type("Sfx_Constellation_Star_Stop", _clad_enum.Sfx_Constellation_Star_Stop)

    #: Plays egg cracking sound.
    Sfx_Egg_Decorating_Crack = _entry_type("Sfx_Egg_Decorating_Crack", _clad_enum.Sfx_Egg_Decorating_Crack)
    #: Stops all active plays of the egg cracking sound.
    Sfx_Egg_Decorating_Crack_Stop = _entry_type("Sfx_Egg_Decorating_Crack_Stop", _clad_enum.Sfx_Egg_Decorating_Crack_Stop)

    #: Plays fidget spinner loop.
    Sfx_Fidget_Spinner_Loop_Play = _entry_type("Sfx_Fidget_Spinner_Loop_Play", _clad_enum.Sfx_Fidget_Spinner_Loop_Play)
    #: Stops all the fidget spinned looping sound.
    Sfx_Fidget_Spinner_Loop_Stop = _entry_type("Sfx_Fidget_Spinner_Loop_Stop", _clad_enum.Sfx_Fidget_Spinner_Loop_Stop)
    #: Plays fidget spinner sound.
    Sfx_Fidget_Spinner_Start = _entry_type("Sfx_Fidget_Spinner_Start", _clad_enum.Sfx_Fidget_Spinner_Start)
    #: Stops all active plays of the fidget spinner sound.
    Sfx_Fidget_Spinner_Start_Stop = _entry_type("Sfx_Fidget_Spinner_Start_Stop", _clad_enum.Sfx_Fidget_Spinner_Start_Stop)

    #: Plays flappy sound.
    Sfx_Flappy_Increase = _entry_type("Sfx_Flappy_Increase", _clad_enum.Sfx_Flappy_Increase)
    #: Stops all active plays of the flappy sound.
    Sfx_Flappy_Increase_Stop = _entry_type("Sfx_Flappy_Increase_Stop", _clad_enum.Sfx_Flappy_Increase_Stop)

    #: Plays morse code dash sound.
    Sfx_Morse_Code_Dash = _entry_type("Sfx_Morse_Code_Dash", _clad_enum.Sfx_Morse_Code_Dash)
    #: Stops all active plays of the morse code dash sound.
    Sfx_Morse_Code_Dash_Stop = _entry_type("Sfx_Morse_Code_Dash_Stop", _clad_enum.Sfx_Morse_Code_Dash_Stop)
    #: Plays morse code dot sound.
    Sfx_Morse_Code_Dot = _entry_type("Sfx_Morse_Code_Dot", _clad_enum.Sfx_Morse_Code_Dot)
    #: Stops all active plays of the morse code dot sound.
    Sfx_Morse_Code_Dot_Stop = _entry_type("Sfx_Morse_Code_Dot_Stop", _clad_enum.Sfx_Morse_Code_Dot_Stop)
    #: Plays morse code silent sound.
    Sfx_Morse_Code_Silent = _entry_type("Sfx_Morse_Code_Silent", _clad_enum.Sfx_Morse_Code_Silent)
    #: Stops all active plays of the morse code silent sound.
    Sfx_Morse_Code_Silent_Stop = _entry_type("Sfx_Morse_Code_Silent_Stop", _clad_enum.Sfx_Morse_Code_Silent_Stop)

    #: Plays paddle ball bounce sound.
    Sfx_Paddle_Ball_Bounce = _entry_type("Sfx_Paddle_Ball_Bounce", _clad_enum.Sfx_Paddle_Ball_Bounce)
    #: Stops all active plays of the paddle ball bounce sound.
    Sfx_Paddle_Ball_Bounce_Stop = _entry_type("Sfx_Paddle_Ball_Bounce_Stop", _clad_enum.Sfx_Paddle_Ball_Bounce_Stop)
    
    #: Plays the first pot of gold sound sound.
    Sfx_Pot_O_Gold_Blip_Level1 = _entry_type("Sfx_Pot_O_Gold_Blip_Level1", _clad_enum.Sfx_Pot_O_Gold_Blip_Level1)
    #: Stops all active plays of the first pot of gold blip sound.
    Sfx_Pot_O_Gold_Blip_Level1_Stop = _entry_type("Sfx_Pot_O_Gold_Blip_Level1_Stop", _clad_enum.Sfx_Pot_O_Gold_Blip_Level1_Stop)
    #: Plays the second pot of gold sound sound.
    Sfx_Pot_O_Gold_Blip_Level2 = _entry_type("Sfx_Pot_O_Gold_Blip_Level2", _clad_enum.Sfx_Pot_O_Gold_Blip_Level2)
    #: Stops all active plays of the second pot of gold blip sound.
    Sfx_Pot_O_Gold_Blip_Level2_Stop = _entry_type("Sfx_Pot_O_Gold_Blip_Level2_Stop", _clad_enum.Sfx_Pot_O_Gold_Blip_Level2_Stop)
    #: Plays the third pot of gold sound sound.
    Sfx_Pot_O_Gold_Blip_Level3 = _entry_type("Sfx_Pot_O_Gold_Blip_Level3", _clad_enum.Sfx_Pot_O_Gold_Blip_Level3)
    #: Stops all active plays of the third pot of gold blip sound.
    Sfx_Pot_O_Gold_Blip_Level3_Stop = _entry_type("Sfx_Pot_O_Gold_Blip_Level3_Stop", _clad_enum.Sfx_Pot_O_Gold_Blip_Level3_Stop)

AudioEvents._init_class(warn_on_missing_definitions=False)
