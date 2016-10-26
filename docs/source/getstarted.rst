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
5. On the computer, open a Terminal (iOS/Linux) / Command Prompt (Windows) window. Type ``cd cozmo_sdk_examples`` where *cozmo_sdk_examples* is the name of the directory you extracted the SDK examples into and press Enter. The SDK example scripts can be downloaded from the :doc:`Downloads page </downloads>`.
6. Now you can run any of the example programs.

----------------
Example Programs
----------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^
First Steps - "Hello World"
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's test your new setup by running a very simple program. This program instructs Cozmo to say "Hello, World!" - a perfect way to introduce him and you to the world of programming.

"""""""""""
The Program
"""""""""""

1. To run the program, using the same Terminal (iOS/Linux) / Command Prompt (Windows) window mentioned above:

    a. For iOS and Linux systems, type the following and press **Enter**::

        ./hello_world.py

    b. For Windows systems, type the following and press **Enter**::

        py hello_world.py

2. If done correctly, Cozmo will say "Hello, World!"

.. warning:: If Cozmo does not perform as expected, look at the first Terminal window and make sure no error messages appeared. If you continue to have issues, please seek help in the Forums.

The code for the Hello World program is:

.. code-block:: python
  :linenos:

  import sys

  import cozmo

  '''Hello World

  Make Cozmo say 'Hello World' in this simple Cozmo SDK example program.
  '''

  def run(sdk_conn):
    robot = sdk_conn.wait_for_robot()
    robot.say_text("Hello World").wait_for_completed()

  if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.connect(run)

    try:
       cozmo.connect(run)
    except cozmo.ConnectionError as e:
       sys.exit("A connection error occurred: %s" % e)

We can edit this code to make Cozmo say something new. Let's write our first program using this code.

^^^^^^^^^^^^^^^^^^^^^^^^^^
Next Steps - "Night-Night"
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Open a new document in a source code editor or plain-text editor. Free source code editors, such as `Atom <https://atom.io>`_ , `Sublime <https://www.sublimetext.com>`_ , or `TextWrangler <http://www.barebones.com/products/textwrangler/>`_ can be found online. Anki does not provide tech support for third-party source code editors.

2. Copy the code from the Hello World program and paste it into the new document.
3. Each line in the program relates to a specific function. To learn more, see :doc:`the Beginner's Tutorial </tutorial-beginner>`.
4. Move to line 15 in the program.

  1. Select the phrase "Hello World". Do NOT select the parentheses or quotation marks around the phrase; those are necessary for Python to properly parse the command.
  2. Type in the new phrase you would like Cozmo to say. In this example, Cozmo will say "Night Night"::

      robot.say_text("Night Night").wait_for_completed()

5. At the top of the screen, select *File -> Save As*, and save the program as ``nightnight.py``.
6. Now you can run your program:

        a. For iOS and Linux systems, type the following into the same window and press **Enter**::

            ./nightnight.py

        b. For Windows systems, type the following into the same window and press **Enter**::

            py nightnight.py

7. If done correctly, Cozmo will say the new phrase.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
