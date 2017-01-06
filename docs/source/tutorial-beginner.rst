========================================
Programming Cozmo - Beginner's Tutorials
========================================

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

Cozmo is programmed in Python. If you are new to Python, `After Hours Programming <http://www.afterhoursprogramming.com/tutorial/Python/Overview/>`_ and `Codecademy <http://www.codecademy.com/tracks/python>`_ offer beginner's courses in learning Python; `Python.org's website <https://wiki.python.org/moin/BeginnersGuide/NonProgrammers>`_ offers a more comprehensive list of video and web tutorials. This tutorial assumes you have a minimal understanding of programming in general.

----------------
Cozmo SDK Forums
----------------

If you get stuck, encounter any problems, or want to ask questions, please visit the `Cozmo SDK Forums <https://forums.anki.com/>`_.

--------------------------
The Baseline - Hello World
--------------------------

The Hello World program is a good example of the basic pieces used in any Cozmo SDK program.

The code for the Hello World program looks like this.

.. code-block:: python
  :lineno-start: 17

  '''Hello World

  Make Cozmo say 'Hello World' in this simple Cozmo SDK example program.
  '''

  import cozmo


  def cozmo_program(robot: cozmo.robot.Robot):
      robot.say_text("Hello World").wait_for_completed()


  cozmo.run_program(cozmo_program)
..

The breakdown of each part of the program is as follows:

1. ``import cozmo`` allows your program to access the Cozmo SDK code contained within the ``cozmo`` module.
2. Text sandwiched between three ``'`` marks is a Docstring. Docstrings are like comments, and are placed inside code to give information to the user.
3. ``robot.say_text("Hello World").wait_for_completed`` is the core of the program.

  a. ``robot.say_text`` is the function that makes Cozmo speak.
  b. ``("Hello World")`` tells Cozmo what to say.
  c. ``wait_for_completed`` tells Cozmo to finish speaking before doing anything else.

4 The last line runs the program above on Cozmo.


--------------------
Running the Programs
--------------------

Example programs are available from the :doc:`Downloads page </downloads>`. Any programs you write, whether the examples shown here or new programs, should be saved to a new directory of your choice.

.. important:: Do NOT save example programs to the *cozmo_sdk_examples* directory. Doing so will overwrite the original baseline programs.

..

To run a program for Cozmo:

.. important:: The usbmuxd (USB Multiplexor Daemon) must be installed on any computer system paired with an iOS device before running any programs. Installing `iTunes <http://www.apple.com/itunes/download/>`_ will also install the usbmuxd on those systems. Linux users can install the usbmuxd module through the command line with `sudo apt-get install usbmuxd`.

.. important:: Make sure adb (Android Debug Bridge) is installed on your system prior to running a program with an Android device. See the :ref:`Install page <initial>` for instructions.

1. Plug the mobile device containing the Cozmo app into your computer.
2. Open the Cozmo app on the device. Make sure Cozmo is on and connected to the app via WiFi.
3. On the computer, open a Terminal (macOS/Linux) / Command Prompt (Windows) window. Type ``cd cozmo_sdk_examples`` where *cozmo_sdk_examples* is the name of the directory you extracted the SDK example programs into and press Enter.
4. Now you can run your program.

  a. For macOS and Linux systems, type the following into the same window and press **Enter**::

      python3 program_name.py

  b. For Windows systems, type the following into the same window and press **Enter**::

      py program_name.py

5. If done correctly, Cozmo will execute the program.

----------------
Example Programs
----------------

^^^^^^^^^^^^^^^^^^^^^^^^^^
Example 1 - Drive Straight
^^^^^^^^^^^^^^^^^^^^^^^^^^

For your first program, you will tell Cozmo to drive in a straight line for a short distance. This program will give you a simple overview of the programming process, as well as some of the building blocks necessary for the programs to work.

1. In your source code editor, create a new document (*File -> New Document*). Free source code editors, such as `PyCharm Community Edition <https://www.jetbrains.com/pycharm/>`_ , `Atom <https://atom.io>`_ , `Sublime <https://www.sublimetext.com>`_ , or `TextWrangler <http://www.barebones.com/products/textwrangler>`_ can be found online. Anki does not provide tech support for third-party source code editors.
2. First, you need to tell the program to import some important information. Type the following lines into your document exactly as shown:

.. code-block:: python
  :linenos:

  import cozmo
  from cozmo.util import distance_mm, speed_mmps

..

  a. ``import cozmo`` allows your program to access the Cozmo SDK code contained within the ``cozmo`` module.
  b. ``from cozmo.util import distance_mm, speed_mmps`` allows your program to specify distances and speeds for Cozmo.

3. Next, you need to tell the program wait for Cozmo to connect. Type the following lines into the document exactly as shown:

.. code-block:: python
  :lineno-start: 4

  def cozmo_program(robot: cozmo.robot.Robot):

4. Now type in the following command as shown:

.. code-block:: python
  :lineno-start: 5

      robot.drive_straight(distance_mm(150), speed_mmps(50)).wait_for_completed()

..

  a. The ``drive_straight`` function creates an action on Cozmo that drives him in a straight line.
  b. ``distance_mm(150)`` is the distance to drive (150 millimeters)
  c. ``speed_mmps(50)`` is the speed to drive at (50 millimeters per second)
  d. ``wait_for_completed()`` instructs the program to wait until the drive_straight action has finished before continuing.

5. Type in the last line:

.. code-block:: python
  :lineno-start: 7

  cozmo.run_program(cozmo_program)

..

    a. ``cozmo.run_program(cozmo_program)`` tells the SDK to run the ``def cozmo_program`` function above as soon as Cozmo connects to the computer.

6. Save the file in the directory of your choice as ``drive_forward.py``.

The completed program should look like this.

.. code-block:: python
  :linenos:

  import cozmo
  from cozmo.util import distance_mm, speed_mmps

  def cozmo_program(robot: cozmo.robot.Robot):
    robot.drive_straight(distance_mm(150), speed_mmps(50)).wait_for_completed()

  cozmo.run_program(cozmo_program)

..

^^^^^^^^^^^^^^^^^^^^^^^
Example 2 - Turn Around
^^^^^^^^^^^^^^^^^^^^^^^

Now that you have written your first program, you're ready to write a more complex program. In this example, you will tell Cozmo to make a 90 degree turn in place and play a victory animation.

1. In your source code editor, create a new document (*File -> New Document*).
2. As in the first example, type the following lines into your document exactly as shown:

.. code-block:: python
  :linenos:

  import cozmo
  from cozmo.util import degrees

..

  a. ``from cozmo.util import degrees`` is a utility that makes it easy to use degrees as a standard of measurement.

3. Next, you need to tell the program wait for Cozmo to connect. Type the following lines into the document exactly as shown:

.. code-block:: python
  :lineno-start: 4

  def cozmo_program(robot: cozmo.robot.Robot):

4. Now type in the following command as shown:

.. code-block:: python
  :lineno-start: 5

      robot.turn_in_place(degrees(90)).wait_for_completed()

..

  a. ``robot.turn_in_place`` directs Cozmo to turn in place.
  b. ``(degrees(90))`` sets how far he turns in relation to where he is. Cozmo's initial position is assumed to be 0 degrees; he will turn 90 degrees, or directly to his left. The number of degrees goes from 0 - 180, where 0 will not move him and 179.99 moves him in almost a semi-circle going counter-clockwise. To make Cozmo turn clockwise, enter a negative number. For example, entering -90 makes Cozmo turn 90 degrees to the right.
  c. ``wait_for_completed()`` makes sure Cozmo completes his turn before performing his next action.

5. Next, type in:

.. code-block:: python
  :lineno-start: 7

      anim = robot.play_anim_trigger(cozmo.anim.Triggers.MajorWin)
      anim.wait_for_completed()

..

  a. ``anim = robot.play_anim_trigger(cozmo.anim.Triggers.MajorWin)`` triggers Cozmo to play a specific animation - in this case, his "Major Win" happy dance.
  b. ``anim.wait_for_completed`` is a signal that makes sure Cozmo completes his dance before performing his next action.

6. Type in the last line:

.. code-block:: python
  :lineno-start: 10

  cozmo.run_program(cozmo_program)

7. Save the file as ``turn.py``.

The completed program should look like this.

.. code-block:: python
  :linenos:

  import cozmo
  from cozmo.util import degrees

  def cozmo_program(robot: cozmo.robot.Robot):
      robot.turn_in_place(degrees(90)).wait_for_completed()

      anim = robot.play_anim_trigger(cozmo.anim.Triggers.MajorWin)
      anim.wait_for_completed()

  cozmo.run_program(cozmo_program)

..

^^^^^^^^^^^^^^^^^^^^^^^
Example 3 - Cube Stack
^^^^^^^^^^^^^^^^^^^^^^^

As a third beginning tutorial, you can tell Cozmo to look around for his blocks, and to stack them one atop the other once he sees two of them.

1. In your source code editor, create a new document (*File -> New Document*).
2. As in the first example, type the following lines into your document exactly as shown:

.. code-block:: python
  :linenos:

  import cozmo

  def cozmo_program(robot: cozmo.robot.Robot):

3. Now type in the following command as shown:

.. code-block:: python
  :lineno-start: 4

      lookaround = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

      cubes = robot.world.wait_until_observe_num_objects(num=2, object_type=cozmo.objects.LightCube, timeout=60)

      lookaround.stop()

..

  1. ``robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAround)``

    a. ``robot.start_behavior`` initiates a specific behavior.
    b. ``cozmo.behavior.BehaviorTypes.LookAround`` is a special behavior where Cozmo will actively move around and search for objects.

  2. ``robot.world.wait_until_observe_num_objects`` directs Cozmo to wait until his sensors detect a specified number of objects.
  3. ``num=2`` specifies the number of objects Cozmo has to find in order to trigger the next behavior.
  4. ``object_type=cozmo.objects.LightCube`` directs Cozmo to specifically find his Cubes. He will not count other objects, such as his charger or other objects on the play area.
  5. ``timeout=60`` sets how long Cozmo will look for Cubes. Timeout is set in seconds.
  6. ``lookaround.stop()`` stops the behavior once it reaches the time limit.

4. Type in the following as shown:

.. code-block:: python
  :lineno-start: 10

      if len(cubes) < 2:
          print("Error: need 2 Cubes but only found", len(cubes), "Cube(s)")
..

  a. ``if len(cubes) < 2:`` is an argument that is called if Cozmo detects fewer than two cubes.
  b. ``print("Error: need 2 Cubes but only found", len(cubes), "Cube(s)")`` is the error message that prints telling the user how many cubes Cozmo saw while looking around.

5. Type in the next line as shown:

.. code-block:: python
  :lineno-start: 12

      else:
          robot.pickup_object(cubes[0]).wait_for_completed()
          robot.place_on_object(cubes[1]).wait_for_completed()

..

  a. ``robot.pickup_object`` directs Cozmo to pick up an object. Note that currently, Cozmo can only pick up his Cubes.
  b. ``(cubes[0])`` specifies the Cube Cozmo needs to pick up; in this case, it is the first Cube Cozmo detected.
  c. ``wait_for_completed()`` is a signal that makes sure Cozmo completes his action before performing his next action.
  d. ``robot.place_on_object`` directs Cozmo to place the object he is holding on top of another object.
  e. ``(cubes[1])`` specifies the Cube Cozmo needs to place what he is holding onto; in this case, it is the second Cube Cozmo detected.
  f. ``wait_for_completed()`` is a signal that makes sure Cozmo completes his action before performing his next action.

6. Type in the last line:

.. code-block:: python
  :lineno-start: 16

  cozmo.run_program(cozmo_program)

..

7. Save the file on your computer as ``cubestack.py``.

The completed program should look like this.

.. code-block:: python
  :linenos:

  import cozmo

  def cozmo_program(robot: cozmo.robot.Robot):
      lookaround = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

      cubes = robot.world.wait_until_observe_num_objects(num=2, object_type=cozmo.objects.LightCube, timeout=60)

      lookaround.stop()

      if len(cubes) < 2:
          print("Error: need 2 Cubes but only found", len(cubes), "Cube(s)")
      else:
          robot.pickup_object(cubes[0]).wait_for_completed()
          robot.place_on_object(cubes[1]).wait_for_completed()

  cozmo.run_program(cozmo_program)

..

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Example 4 - Sing the Scales
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Building further on previously introduced code, let's combine your new knowledge on movement with the knowledge gained with the "Hello World" program to make Cozmo sing the scales.

1. In your source code editor, create a new document (*File -> New Document*).
2. The code for the program is listed below.

  .. code-block:: python
    :lineno-start: 17

    '''Make Cozmo sing Do Re Mi.

    Make Cozmo "sing" the scales.
    This is a small extension of the 03_count.py example.
    '''

    import cozmo
    from cozmo.util import degrees


    def cozmo_program(robot: cozmo.robot.Robot):
        # scales is a list of the words for Cozmo to sing
        scales = ["Doe", "Ray", "Mi", "Fa", "So", "La", "Ti", "Doe"]

        # Find voice_pitch_delta value that will range the pitch from -1 to 1 over all of the scales
        voice_pitch = -1.0
        voice_pitch_delta = 2.0 / (len(scales) - 1)

        # Move head and lift down to the bottom, and wait until that's achieved
        robot.move_head(-5) # start moving head down so it mostly happens in parallel with lift
        robot.set_lift_height(0.0).wait_for_completed()
        robot.set_head_angle(degrees(-25.0)).wait_for_completed()

        # Start slowly raising lift and head
        robot.move_lift(0.15)
        robot.move_head(0.15)

        # "Sing" each note of the scale at increasingly high pitch
        for note in scales:
            robot.say_text(note, voice_pitch=voice_pitch, duration_scalar=0.3).wait_for_completed()
            voice_pitch += voice_pitch_delta


    cozmo.run_program(cozmo_program)

..

The new code elements introduced in this section are as follows:
  1. ``voice_pitch`` and ``voice_pitch_delta``

      a. ``voice_pitch`` adjusts the pitch of Cozmo's voice. The valid range for pitch is on a scale from -1.0 to 1.0.
      b. ``voice_pitch_delta`` defines the valid range of Cozmo's voice pitch. The value of 2.0 is what sets the range to be from -1.0 to 1.0. Values in this line of code should not be changed.

  2. ``robot.move_head(-5)`` moves Cozmo's head down.
  3. ``robot.set_lift_height(0.0)`` sets the position of his lift. ``(0.0)`` is the lift's neutral starting position.
  4. ``robot.set_head_angle`` sets the angle Cozmo should tilt his head. In this example, it is set to degrees. ``(-25.0)`` sets the specific angle to 25 degrees tilted down.
  5. The values of ``robot.move_lift`` and ``robot.move_head`` are then set the same so that the head and lift will move in unison.
  6. The variables within the ``robot.say_text`` directive denotes what Cozmo will say, the pitch he will speak at, and the relative time period over which Cozmo will sing.
  7. ``voice_pitch += voice_pitch_delta`` sets it so that Cozmo's voice will rise in pitch with each word he says.

Save the file as ``sing_scales.py`` on your computer when completed.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
