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

'''Quiz-master Cozmo - a simple quiz game hosted by Cozmo.

Uses the 3 cubes as buzzers for a quiz with up to 3 players.
'''

import asyncio
import json
from random import randrange, shuffle

import cozmo


class QuizQuestion:
    """A single multiple choice question with 4 choices, one correct.
    
    Args:
        question (str): The question.
        answer_options (list of str): 4 multiple choice answers where the
            1st element is the correct answer. (Choices will be shuffled each time.)
    Raises:
        :class:`ValueError` if not supplied exactly 4 answer_options.
    """
    def __init__(self, question, answer_options):
        if len(answer_options) != 4:
            raise ValueError("Expected 4 answer_options, got %s" % len(answer_options))
        self.question = question
        self._answer_index = 0
        self.answer_options = list(answer_options)  # copy the answer_options, so we can shuffle them
        self.shuffle_answer_options()

    @property
    def answer_number(self):
        """int: The number (i.e. 1, 2, 3 or 4) representing the correct answer."""
        return self._answer_index + 1

    @property
    def answer_str(self):
        """str: The string representing the correct answer."""
        return self.answer_options[self._answer_index]

    def shuffle_answer_options(self):
        """Shuffle the answer_options so that they're not always read in the same order."""

        # to shuffle whilst keeping track of the answer, we first pop the
        # answer out, shuffle the rest, and then insert the answer at a random
        # known point.
        answer = self.answer_options.pop(self._answer_index)
        shuffle(self.answer_options)
        self._answer_index = randrange(len(self.answer_options)+1)
        self.answer_options.insert(self._answer_index, answer)


class CozmoQuizPlayer:
    """A player in the quiz.

    Args:
        robot (:class:`cozmo.robot.Robot`): The cozmo robot.
        cube (:class:`cozmo.objects.LightCube`): This player's cube.
        index(int): The number (i.e. 0, 1 or 2) specifying the index of this player and cube.
        color(:class:`cozmo.lights.Light`): The light color for this player.
        name(str): The name of this player.
    """
    def __init__(self,
                 robot: cozmo.robot.Robot,
                 cube: cozmo.objects.LightCube, index, color, name):
        self._robot = robot
        self._cube = cube
        self._index = index
        self._color = color
        self.name = name
        self.score = 0
        self._has_buzzed_in = False
        self._answer_index = 0

    def verify_setup(self):
        # Return True if and only if the player was setup correctly and has a connected cube.
        success = True
        if self._cube is None:
            cozmo.logger.warning("Cozmo is not connected to a cube %s - check the battery.", (self._index+1))
            success = False
        return success

    def reset_for_question(self):
        self.turn_light_on()
        self._has_buzzed_in = False

    def turn_light_off(self):
        if self._cube is not None:
            self._cube.set_lights_off()

    def turn_light_on(self):
        if self._cube is not None:
            self._cube.set_lights(self._color)

    def set_answer_light(self):
        if self._cube is not None:
            # lights up from 1 to 4 lights in a clockwise order to indicate the
            # current selected answer.
            cols = [cozmo.lights.off_light] * 4
            for i in range(self.answer_number):
                # We index cols in reverse order so they light up in a clockwise order.
                cols[3-i] = self._color
            self._cube.set_light_corners(*cols)

    def on_buzzed_in(self):
        # Called when the player buzzes in for a question.
        self.turn_light_on()
        self._has_buzzed_in = True

    def start_answering(self):
        # Called when the player starts answering a question.
        self._answer_index = 0
        self.set_answer_light()

    def cycle_answer(self):
        # Called every time a player taps the cube to cycle through the 4 answer answer_options.
        self._answer_index += 1
        if self._answer_index > 3:
            self._answer_index = 0
        self.set_answer_light()

    @property
    def object_id(self):
        if self._cube is None:
            return None
        else:
            return self._cube.object_id

    @property
    def has_buzzed_in(self):
        """bool: True if this player has buzzed in for this question already."""
        return self._has_buzzed_in

    @property
    def answer_number(self):
        """int: The number (1..4) representing this player's answer."""
        return self._answer_index + 1


class CozmoQuizMaster:
    """Cozmo the robot quiz master.
    
    Maintains the list of questions and the players, and runs the quiz.

    Args:
        robot (:class:`cozmo.robot.Robot`): The cozmo robot.
    """
    def __init__(self, robot: cozmo.robot.Robot):
        self._robot = robot

        # initialize the list of players
        cube_ids = cozmo.objects.LightCubeIDs
        cube_colors = [cozmo.lights.red_light, cozmo.lights.green_light, cozmo.lights.blue_light]
        player_names = ["Red", "Green", "Blue"]
        self._players = []  # type: list of CozmoQuizPlayer
        for i in range(len(cube_ids)):
            cube = robot.world.get_light_cube(cube_ids[i])
            player = CozmoQuizPlayer(robot, cube, i, cube_colors[i], player_names[i])
            self._players.append(player)

        self._answering_player = None  # type: CozmoQuizPlayer
        self._buzzing_in_accepted = False
        self._answers_accepted = False
        self._questions = []

        with open("quiz_questions.json") as data_file:
            data = json.load(data_file)

        for quiz_question_json in data:
            question = quiz_question_json["question"]
            answer_options = quiz_question_json["answer_options"]
            self._questions.append(QuizQuestion(question, answer_options))

    def verify_setup(self):
        # return True if and only if everything is setup correctly
        num_valid_players = 0
        for player in self._players:
            if player.verify_setup():
                num_valid_players += 1
        return (num_valid_players > 0)

    def get_player_for_object_id(self, object_id):
        for player in self._players:
            if player.object_id == object_id:
                return player
        cozmo.logger.warn("No player for object_id %s", object_id)
        return None

    def on_cube_tapped(self, evt, **kw):
        # find the player for that cube, and handle the tap as appropriate
        player = self.get_player_for_object_id(evt.obj.object_id)
        if self._buzzing_in_accepted and self._answering_player is None:
            if player and not player.has_buzzed_in:
                self._answering_player = player
                player.on_buzzed_in()
        elif self._answers_accepted and player == self._answering_player:
            if player:
                player.cycle_answer()

    def turn_player_lights_on(self):
        for player in self._players:
            player.turn_light_on()

    def turn_player_lights_off(self):
        for player in self._players:
            player.turn_light_off()

    def get_next_question(self) -> QuizQuestion:
        if len(self._questions) > 0:
            i = randrange(len(self._questions))
            question = self._questions.pop(i)
            return question
        else:
            print("Out of questions!")
            return None

    def create_answer_options_string(self, list_of_answer_options) -> str:
        # Build a string that lists all of the answer_options in order.
        text = "Is it "
        for i in range(len(list_of_answer_options)):
            conjunction = ""
            if i > 0:
                is_last_option = (i == (len(list_of_answer_options) - 1))
                conjunction = " or " if is_last_option else ", "
            text += conjunction + str(i+1) + ": " + list_of_answer_options[i]
        return text

    def say_text(self, text, in_parallel=False):
        print("%s" % text)
        return self._robot.say_text(text, in_parallel=in_parallel)

    async def wait_for_answer(self, player):
        # Wait for player's answer (whatever the player leaves selected after x seconds)
        # This is after Cozmo has finished speaking, so we've already given the
        # player a few seconds.
        await asyncio.sleep(2.0)
        return player.answer_number

    def get_winning_players(self):
        # get a list of all the players with the top score
        winning_players = []
        for player in self._players:
            if len(winning_players) == 0 or player.score > winning_players[0].score:
                winning_players = [player]
            elif player.score == winning_players[0].score:
                winning_players.append(player)
        return winning_players

    async def report_leader(self, is_final_score):
        # Report the leading / winning player(s)
        winning_players = self.get_winning_players()
        winning_score = winning_players[0].score
        points_string = "points" if (winning_score != 1) else "point"
        winning_score_str = "%s %s" % (winning_score, points_string)

        if len(winning_players) == len(self._players):
            if is_final_score:
                action = self.say_text("It ends as a draw with everyone at %s" % winning_score_str)
            else:
                action = self.say_text("It's all tied at %s" % winning_score_str)
        else:
            winner_names = winning_players[0].name
            for i in range(1, len(winning_players)):
                # separate winner names with commas, but use 'and' for the last one
                is_last_player = (i == (len(winning_players)-1))
                conjunction = " and " if is_last_player else ", "
                winner_names = winner_names + conjunction + winning_players[i].name

            if is_final_score:
                action = self.say_text("%s won with %s" % (winner_names, winning_score_str))
            else:
                is_or_are = "is" if len(winning_players) == 1 else "are"
                action = self.say_text("%s %s in the lead with %s" %
                                       (winner_names, is_or_are, winning_score_str))

        await action.wait_for_completed()

    async def get_correct_player(self, question: QuizQuestion):
        # Read the answer_options
        read_options_action = self.say_text(self.create_answer_options_string(question.answer_options))
        num_answers = 0

        # Let the player(s) buzz in and answer
        for _ in range(len(self._players)):
            if num_answers > 0:
                read_options_action = self.say_text("Anyone else?")

            # wait for a player to buzz in before the answer finishes
            while not read_options_action.is_completed and self._answering_player is None:
                await asyncio.sleep(0.1)

            if self._answering_player is None:
                # question reading finished, give them 1 more second to buzz in
                await asyncio.sleep(1.0)

            player = self._answering_player
            if player is None:
                # Nobody answered in time
                await read_options_action.wait_for_completed()
                return None

            # short wait before accepting player answer, so we don't incorrectly
            # identify late buzzes as cycling the answer
            await asyncio.sleep(0.5)

            # Start accepting taps from the answering player
            player.start_answering()
            self._answers_accepted = True

            await read_options_action.wait_for_completed()
            action = self.say_text(player.name + "?")
            await action.wait_for_completed()

            player_answer = await self.wait_for_answer(player)
            self._answers_accepted = False
            num_answers += 1

            if player_answer == question.answer_number:
                # Correct
                player.score += 1
                return player
            else:
                # Incorrect
                player.score -= 1
                action = self._robot.play_anim_trigger(cozmo.anim.Triggers.KnockOverFailure)
                self._answering_player = None
                player.turn_light_off()
                await action.wait_for_completed()

    async def ask_question(self, question: QuizQuestion):
        # Reset for a new question
        for player in self._players:
            player.reset_for_question()
        self._answering_player = None
        self._buzzing_in_accepted = False
        self._answers_accepted = False

        # Read the question
        action = self.say_text(question.question)
        await action.wait_for_completed()

        # Allow buzzing in
        self.turn_player_lights_off()
        self._buzzing_in_accepted = True

        correct_player = await self.get_correct_player(question)
        if correct_player is None:
            # Nobody answered correctly
            action = self._robot.play_anim_trigger(cozmo.anim.Triggers.FailedToRightFromFace)
            await action.wait_for_completed()
            action = self.say_text("The answer was %s: %s" % (question.answer_number, question.answer_str))
            await action.wait_for_completed()
        else:
            # Correct
            action = self._robot.play_anim_trigger(cozmo.anim.Triggers.ReactToBlockPickupSuccess)
            await action.wait_for_completed()
            action = self.say_text("Correct it was %s: %s" % (question.answer_number, question.answer_str))
            await action.wait_for_completed()

    async def run(self):
        # Exit immediately if setup failed
        if not self.verify_setup():
            return

        # Add a handler so that we can track whenever a cube is tapped
        self._robot.add_event_handler(cozmo.objects.EvtObjectTapped, self.on_cube_tapped)

        # Keep asking questions until there are none left
        while True:
            question = self.get_next_question()
            if question:
                await self.ask_question(question)
            else:
                print("Quiz is complete!")
                await self.report_leader(True)
                action = self._robot.play_anim_trigger(cozmo.anim.Triggers.BuildPyramidSuccess)
                await action.wait_for_completed()
                action = self.say_text("Game Over - Bye!")
                await action.wait_for_completed()
                return


async def cozmo_program(robot: cozmo.robot.Robot):
    quiz_master = CozmoQuizMaster(robot)
    await quiz_master.run()


cozmo.run_program(cozmo_program)
