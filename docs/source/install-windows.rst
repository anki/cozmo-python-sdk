.. _install-windows:

######################
Installation - Windows
######################

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

This guide provides instructions on installing the Cozmo SDK for computers running with a Windows operating system.

^^^^^^^^^^^^^^^^^^^
Installation Videos
^^^^^^^^^^^^^^^^^^^

For your convenience, videos are provided showing the installation steps being followed on a Windows computer; one using an iOS device, and one using an Android device. There is also full text-based documentation below these.

.. raw:: html

   <iframe width="690" height="388" src="https://www.youtube.com/embed/gtRS3iqzSuA?rel=0" frameborder="0" allowfullscreen></iframe>

   <iframe width="690" height="388" src="https://www.youtube.com/embed/9TJeK_AEFYo?rel=0" frameborder="0" allowfullscreen></iframe>   

|

^^^^^^^^^^^^^^^^^^^
Python Installation
^^^^^^^^^^^^^^^^^^^

Download the `Python 3.5.1 (or later) executable file from Python.org <https://www.python.org/downloads/>`_ and
run it on your computer.

.. important:: We recommend that you tick the "Add Python 3.5 to PATH" checkbox on the Setup screen.

^^^^^^^^^^^^^^^^
SDK Installation
^^^^^^^^^^^^^^^^

To install the SDK, type the following into the Command Prompt window::

    pip3 install --user cozmo[camera]

Note that the [camera] option adds support for processing images from Cozmo's camera.

"""""""""""
SDK Upgrade
"""""""""""

To upgrade the SDK from a previous install, enter this command::

    pip3 install --user --upgrade cozmo

^^^^^^^^^^^^^^^^^^^
Mobile Device Setup
^^^^^^^^^^^^^^^^^^^

* **iOS** devices require `iTunes <http://www.apple.com/itunes/download/>`_ to ensure that the usbmuxd service is installed on your computer. Usbmuxd is required for the computer to communicate with the iOS device over a USB cable. While iTunes needs to be installed, it does not need to be running.

* **Android** devices require installation of :ref:`adb` (adb) in order to run the Cozmo SDK. This is required for the computer to communicate with the Android mobile device over a USB cable and runs automatically when required.

^^^^^^^^^^^^^^^
Troubleshooting
^^^^^^^^^^^^^^^

Please see the :ref:`trouble` section of the Initial Setup page for tips, or visit the `Cozmo SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions, or for general discussion.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
