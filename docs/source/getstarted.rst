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
5. On the computer, open a Terminal (macOS/Linux) / Command Prompt (Windows) window. Type ``cd cozmo_sdk_examples`` where *cozmo_sdk_examples* is the name of the directory you extracted the SDK examples into and press Enter. The SDK example scripts can be downloaded from the :doc:`Downloads page </downloads>`.
6. Now you can run any of the example programs.

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
First Steps - "Hello World"
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

    b. For Windows systems, type the following and press **Enter**::

        py 01_hello_world.py

2. If done correctly, Cozmo will say "Hello, World!"

.. warning:: If Cozmo does not perform as expected, look at the first Terminal window and make sure no error messages appeared. If you continue to have issues, please seek help in the Forums.

The code for the Hello World program can be `viewed here. <https://github.com/anki/cozmo-python-sdk/tree/master/examples/tutorials/01_basics/01_hello_world.py>`_

We can edit this code to make Cozmo say something new. Let's write our first program using this code.

^^^^^^^^^^^^^^^^^^^^^^^^^^
Next Steps - "Night-Night"
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Copy ``01_hello_world.py`` to a new file named ``nightnight.py``.

    a. For macOS and Linux systems, type the following and press **Enter**::

        cp 01_hello_world.py nightnight.py

    b. For Windows systems, type the following and press **Enter**::

        copy 01_hello_world.py nightnight.py
    
2. Open this new document in a source code editor or plain-text editor. Free source code editors, such as `PyCharm Community Edition <https://www.jetbrains.com/pycharm/>`_ , `Atom <https://atom.io>`_ , `Sublime <https://www.sublimetext.com>`_ , or `TextWrangler <http://www.barebones.com/products/textwrangler/>`_ can be found online. Anki does not provide tech support for third-party source code editors.

3. Each line in the program relates to a specific function. To learn more, see :doc:`the Beginner's Tutorial </tutorial-beginner>`.

4. Move to the line that starts with "robot.say_text"

  1. Select the phrase "Hello World". Do NOT select the parentheses or quotation marks around the phrase; those are necessary for Python to properly parse the command.
  2. Type in the new phrase you would like Cozmo to say. In this example, Cozmo will say "Night Night"::

      robot.say_text("Night Night").wait_for_completed()

5. Save the nightnight.py file.
6. Now you can run your program:

        a. For macOS and Linux systems, type the following into the same window and press **Enter**::

            ./nightnight.py

        b. For Windows systems, type the following into the same window and press **Enter**::

            py nightnight.py

7. If done correctly, Cozmo will say the new phrase.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
