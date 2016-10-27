.. _install-macos:

###########################
Installation - macOS / OS X
###########################

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

This guide provides instructions on installing the Cozmo SDK for computers running with a macOS operating system.

^^^^^^^^^^^^^^^^^^^
Python Installation
^^^^^^^^^^^^^^^^^^^

1. Install `Homebrew <http://brew.sh>`_ on your system according to the latest instructions. If you already had brew installed then update it by opening a Terminal window and typing in the following::

    brew update

2. Once Homebrew is installed and updated, type the following into the Terminal window to install the latest version of Python 3::

    brew install python3

^^^^^^^^^^^^^^^^
SDK Installation
^^^^^^^^^^^^^^^^

To install the SDK, type the following into the Terminal window::

    pip3 install --user 'cozmo[camera]'

Note that the [camera] option adds support for processing images from Cozmo's camera.

"""""""""""
SDK Upgrade
"""""""""""

To upgrade the SDK from a previous install, enter this command::

    pip3 install --user --upgrade cozmo

^^^^^^^^^^^^^^^^^^^
Mobile Device Setup
^^^^^^^^^^^^^^^^^^^

* **iOS** devices do not require any special setup in order to run the Cozmo SDK on a macOS system.
* **Android** devices require installation of :ref:`adb` (adb) in order to run the Cozmo SDK. This is required for the computer to communicate with the Android mobile device over a USB cable and runs automatically when required.

^^^^^^^^^^^^^^^
Troubleshooting
^^^^^^^^^^^^^^^

Please see the :ref:`trouble` section of the Initial Setup page for tips, or visit the `Cozmo SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions, or for general discussion.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
