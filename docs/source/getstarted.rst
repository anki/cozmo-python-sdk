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

1. Plug the mobile device containing the Cozmo app into your computer.
2. Open the Cozmo app on the phone. Make sure Cozmo is on and connected to the app via WiFi.
3. Tap on the gear icon at the top right corner to open the Settings menu.
4. Swipe left to show the Cozmo SDK option and tap the Enable SDK button.
5. Make sure the SDK examples are downloaded from the :doc:`Downloads page </downloads>`.
6. On the computer, open Terminal (macOS/Linux) or Command Prompt (Windows) and type ``cd cozmo_sdk_examples``, where *cozmo_sdk_examples* is the directory you extracted the examples into, and press **Enter**.

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

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
First Steps - "Hello, World!"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

    The same can also be achieved on macOS/Linux with:
	
        python3 01_hello_world.py

    b. For Windows systems, type the following and press **Enter**::

        py 01_hello_world.py

2. If done correctly, Cozmo will say "Hello, World!"

.. warning:: If Cozmo does not perform as expected, look at the first Terminal window and make sure no error messages appeared. If you continue to have issues, please seek help in the Forums.

The code for the Hello World program can be `viewed here. <https://github.com/anki/cozmo-python-sdk/tree/master/examples/tutorials/01_basics/01_hello_world.py>`_

.. important:: The usbmuxd (USB Multiplexor Daemon) must be installed on any computer system paired with an iOS device before running any programs. Installing `iTunes <http://www.apple.com/itunes/download/>`_ will also install the usbmuxd on those systems. Linux users can install the usbmuxd module through the command line with `sudo apt-get install usbmuxd`.

.. important:: Make sure adb (Android Debug Bridge) is installed on your system prior to running a program with an Android device. See the :ref:`Install page <initial>` for instructions.

You are now all set up to run Python programs on Cozmo. Next we will go over how to edit the above code to make Cozmo say something new. Let's write our first program.

^^^^^^^^^^^^^^^^^^^^^^^^^^
Next Steps - "Night-Night"
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Copy ``01_hello_world.py`` to a new file named ``nightnight.py`` by doing the following:

    a. For macOS and Linux systems, type the following and press **Enter**::

        cp 01_hello_world.py nightnight.py

    b. For Windows systems, type the following and press **Enter**::

        copy 01_hello_world.py nightnight.py

Now, nightnight.py is saved in the same folder as 01_hello_world.py.
	
2. Open this new document in a source code editor or plain-text editor. Free source code editors, such as `PyCharm Community Edition <https://www.jetbrains.com/pycharm/>`_ , `Atom <https://atom.io>`_ , `Sublime <https://www.sublimetext.com>`_ , or `TextWrangler <http://www.barebones.com/products/textwrangler/>`_ can be found online. Anki does not provide tech support for third-party source code editors.

3. Each line in the program relates to a specific function.

    a. ``import cozmo`` allows your program to access the Cozmo SDK code contained within the ``cozmo`` module.
    b. Text sandwiched between three ``'`` marks is a Docstring. Docstrings are like comments, and are placed inside code to give information to the user.
    c. ``robot.say_text("Hello, World!").wait_for_completed()`` is the core of the program:

        i. ``robot.say_text(…)`` is the function that makes Cozmo speak a string out loud.
        ii. ``"Hello World"`` is the string which Cozmo will speak.
        iii. ``wait_for_completed()`` tells Cozmo to finish speaking before moving to the next line of code. Without this, our program would end before Cozmo said anything!

4. Move to the line that starts with "robot.say_text"

    a. Select the phrase "Hello World". Do NOT select the parentheses or quotation marks around the phrase; those are necessary for Python to properly parse the command.
    b. Type in the new phrase you would like Cozmo to say. In this example, Cozmo will say "Night Night", so that line should look like this: ``robot.say_text("Night Night").wait_for_completed()``

5. Save the nightnight.py file.
6. Now you can run your program:

        a. For macOS and Linux systems, type the following into the same Terminal window and press **Enter**::

            ./nightnight.py

        b. For Windows systems, type the following into the same Command Prompt window and press **Enter**::

            py nightnight.py

7. If done correctly, Cozmo will say the new phrase.


Now that you have written your own Cozmo program, take a look at the rest of the Cozmo SDK and at the many other example programs to get more ideas.

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
