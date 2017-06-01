==================================
Getting Started With the Cozmo SDK
==================================

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

To make sure you get the best experience possible out of the SDK, please ensure you have followed the steps in the :doc:`Initial Setup </initial>`.

----------------
Cozmo SDK Forums
----------------

Please visit our `Cozmo SDK Forums <https://forums.anki.com/>`_ where you can:

* Get assistance with your code

* Hear about upcoming SDK additions

* Share your work

* Join discussion about the SDK

* Be a part of the Cozmo SDK Community!


-------------------
Starting Up the SDK
-------------------

1.	Plug the mobile device containing the Cozmo app into your computer.
2.	Open the Cozmo app on the phone. Make sure Cozmo is on and connected to the app via WiFi.
3.	Tap on the gear icon at the top right corner to open the Settings menu.
4.	Swipe left to show the Cozmo SDK option and tap the Enable SDK button.
5.	Make sure the SDK examples are downloaded from the :doc:`Downloads page </downloads>`.  Remove the version number from the folder name so that it is just called “cozmo_sdk_examples”.
6.	To run a program, open Terminal (macOS/Linux) or Command Prompt (Windows) and navigate to the folder containing that program. For example, if the cozmo_sdk_examples folder is saved to your desktop, type ``cd Desktop/cozmo_sdk_examples/tutorials/01_basics``
    NOTE: the forward slash, ‘/‘, is used for macOS/Linux. For Windows, replace forward slash with backslash 

----------------
Example Programs
----------------

^^^^^^^^^^^^^^^^^
Walkthrough Video
^^^^^^^^^^^^^^^^^

For your convenience, here is a video detailing the first few simple example programs. You can also find a simple text-based walkthrough of running your first program below.

.. raw:: html

   <iframe width="690" height="388" src="https://www.youtube.com/embed/YAQ_USpkxgE?rel=0" frameborder="0" allowfullscreen></iframe>

|

^^^^^^^^^^^^^^^^^^^^^^^^^^^
"Hello, World!”
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's test your new setup by running a very simple program. This program instructs Cozmo to say "Hello, World!" - a perfect way to introduce him and you to the world of programming.

"""""""""""
The Program
"""""""""""

1. To run the program, using the same Terminal (macOS/Linux) / Command Prompt (Windows) window mentioned above: 

First, change to the ``01_basics`` sub-directory of the ``tutorials`` directory.

  a. For macOS and Linux systems, type the following and press **Enter**::

    cd tutorials/01_basics

  b. For Windows systems, type the following and press **Enter**::

    cd tutorials\01_basics

Then, run the program.

  a. For macOS and Linux systems, type the following and press **Enter**::

    ./01_hello_world.py

   The same can also be achieved by writing
	
	python3 01_hello_world.py

  b. For Windows systems, type the following and press **Enter**::

    py 01_hello_world.py

2. If done correctly, Cozmo will say "Hello, World!"

.. warning:: If Cozmo does not perform as expected, look at the first Terminal window and make sure no error messages appeared. If you continue to have issues, please seek help in the Forums.

The code for the Hello World program can be `viewed here. <https://github.com/anki/cozmo-python-sdk/tree/master/examples/tutorials/01_basics/01_hello_world.py>`_


You are now all set up to run python programs on Cozmo. Next we will go over how to edit the above code to make Cozmo say something new. Let's write our first program.

^^^^^^^^^^^^^^^^^^^^^^^^^^
"Night-Night"
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Copy ``01_hello_world.py`` to a new file named ``nightnight.py`` by doing the following:

  a. For macOS and Linux systems, type the following and press **Enter**::

    cp 01_hello_world.py nightnight.py

  b. For Windows systems, type the following and press **Enter**::

    copy 01_hello_world.py nightnight.py

Now, nightnight.py is saved in the same folder as 01_hello_world.py.
  
2. Open this new document in a source code editor or plain-text editor. Free source code editors, such as `PyCharm Community Edition <https://www.jetbrains.com/pycharm/>`_ , `Atom <https://atom.io>`_ , `Sublime <https://www.sublimetext.com>`_ , or `TextWrangler <http://www.barebones.com/products/textwrangler/>`_ can be found online. Anki does not provide tech support for third-party source code editors.

3. The code for the program currently looks like this:

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


	a. ``import cozmo`` allows your program to access the Cozmo SDK code contained within the ``cozmo`` module.
	b. Text sandwiched between three ``'`` marks is a Docstring. Docstrings are like comments, and are placed inside code to give information to the user.
	c. ``robot.say_text("Hello World").wait_for_completed`` is the core of the program.
 		i. ``robot.say_text(…)`` is the function that makes Cozmo speak a string out loud.
 		ii. ``"Hello World"`` is the string which Cozmo will speak.
 		iii. ``wait_for_completed()`` tells Cozmo to finish speaking before moving to the next line of code. Without this, our program would end before Cozmo said anything!

4. Move to the line that starts with "robot.say_text"

	a. Select the phrase "Hello World". Do NOT select the parentheses or quotation marks around the phrase; those are necessary for Python to properly parse the command.
	b. Type in the new phrase you would like Cozmo to say. In this example, Cozmo will say "Night Night”, so that line should look like this: ``robot.say_text("Night Night").wait_for_completed()``

5. Save the nightnight.py file.
6. Now you can run your program:

    a. For macOS and Linux systems, type the following into the same Terminal window and press **Enter**::

      ./nightnight.py

    b. For Windows systems, type the following into the same Command Prompt window and press **Enter**::

      py nightnight.py

7. If done correctly, Cozmo will say the new phrase.

Now we will write a Cozmo program more or less from scratch. You will tell Cozmo to drive in a straight line for a short distance, then turn back around and end in his starting position.

^^^^^^^^^^^^^^^^^^^^^^^^^^
“There and Back”
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. In your source code editor, create a new document (*File -> New Document*). 
2. You need to tell the program to import some important information. Type the following lines into your document exactly as shown:

.. code-block:: python
 :linenos:

 import cozmo
 from cozmo.util import distance_mm, speed_mmps, degrees
..

  a. ``import cozmo`` allows your program to access the Cozmo SDK code contained within the ``cozmo`` module.
  b. ``from cozmo.util import distance_mm, speed_mmps, degrees`` allows your program to specify distances and speeds for Cozmo to drive at and degrees for Cozmo to turn around.

3. Next, you need to define the function that Cozmo will execute, called ``cozmo_program``. Type the following lines into the document exactly as shown:

.. code-block:: python
 :lineno-start: 4

 def cozmo_program(robot: cozmo.robot.Robot):
..

  a. In parentheses is the input to the function. Here our input is ``robot: cozmo.robot.Robot``. Before the ``:`` is “robot”, which is the name of our input that we use inside the function.
  b. After the ``:``, we have ``cozmo.robot.Robot``, which specifies the type of our object.  The type of an object determines the way it can be used - in this example, because ``robot`` is of type ``cozmo.robot.Robot``, we will be able to use the functions ``drive_straight`` and ``turn_in_place``.  To read more about which functions a ``cozmo.robot.Robot`` object can use, go to `our API page for cozmo.robot.Robot. <http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot>`_

4. Now type in the following command to have Cozmo drive straight:

.. code-block:: python
 :lineno-start: 5

   robot.drive_straight(distance_mm(150), speed_mmps(50)).wait_for_completed()
..

  a. The ``drive_straight`` function creates an action on Cozmo that drives him in a straight line.  It needs a distance and a speed as input.
  b. ``distance_mm(150)`` is the distance to drive (150 millimeters)
  c. ``speed_mmps(50)`` is the speed to drive at (50 millimeters per second)
  d. ``wait_for_completed()`` instructs the program to wait until the drive_straight action has finished before continuing. Recall that we used the same command with say_text in the Hello World and Night Night examples. Say_text and drive_straight are two of cozmo’s “actions” - we used ``wait_for_completed`` to make sure that Cozmo executes these actions one at a time. Later on we will explore how Cozmo can do multiple things at the same time.

5. Now type in the following command to have Cozmo turn around:

.. code-block:: python
 :lineno-start: 6

 robot.turn_in_place(degrees(180)).wait_for_completed()
..

  a. ``robot.turn_in_place`` directs Cozmo to turn in place.
  b. ``(degrees(180))`` sets how far he turns in relation to where he is. Cozmo's initial position is assumed to be 0 degrees; he will turn 180 degrees, or directly around. To make Cozmo turn clockwise, enter a negative number. For example, entering -90 makes Cozmo turn 90 degrees to the right.
  c. ``wait_for_completed()`` makes sure Cozmo completes his turn before performing his next action.

6. Now copy and paste lines 5 and 6 so that the completed program should look like this:

.. code-block:: python
 :linenos:

 import cozmo
 from cozmo.util import distance_mm, speed_mmps

 def cozmo_program(robot: cozmo.robot.Robot):
  robot.drive_straight(distance_mm(150), speed_mmps(50)).wait_for_completed()
  robot.turn_in_place(degrees(180)).wait_for_completed()
  robot.drive_straight(distance_mm(150), speed_mmps(50)).wait_for_completed()
  robot.turn_in_place(degrees(180)).wait_for_completed()

 cozmo.run_program(cozmo_program)
..

Save this file as there_and_back.py.

Now you can run your program:

    a. For macOS and Linux systems, type the following into the same Terminal window and press **Enter**::

      ./there_and_back.py

    b. For Windows systems, type the following into the same Command Prompt window and press **Enter**::

      py there_and_back.py


Now that you have written your own Cozmo program, take a look at the rest of the Cozmo SDK package at some of our many other example programs to get more ideas. 

^^^^^^^^^^^^^^^^^^^^^^^^^^
Challenges
^^^^^^^^^^^^^^^^^^^^^^^^^^

Some challenges to try once you have explored the examples (these are hard - try your best!):
        
	Have Cozmo drive in a figure-8!
        
	Have Cozmo spin around when you smile at him!
        
	Have Cozmo count cubes as he picks them up!

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
