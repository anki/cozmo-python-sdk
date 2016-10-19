.. _install-osx:

###################
Installation - macOS
###################

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

This guide provides instructions on installing the Cozmo SDK for computers running with a macOS operating system.

-------------------
Python Installation
-------------------

1. Install `Homebrew <http://brew.sh>`_ on your system according to the latest instructions. If you already had brew installed then update it by opening a Terminal window and typing in the following::

    brew update

2. Once Homebrew is installed and updated, type the following into the Terminal window to install the latest version of Python 3::

    brew install python3

-------------------
Mobile Device Setup
-------------------

3. **iOS** devices require `iTunes <http://www.apple.com/itunes/download/>`_ to ensure that the usbmuxd service is installed on your computer. Usbmuxd is required for the computer to communicate with the iOS device over a USB cable. While iTunes needs to be installed, it does not need to be running.

4. **Android** devices require installation of :ref:`adb` (adb) in order to run the Cozmo SDK. Android Debug Bridge is required for the computer to communicate with the Android mobile device over a USB cable. This service automatically runs when required.

----------------
SDK Installation
----------------

To install the SDK, type the following into the Terminal window::

    pip3 install --user cozmo[camera]

Note that the [camera] option adds support for processing images from Cozmo's camera.

^^^^^^^^^^^^^^^
Troubleshooting
^^^^^^^^^^^^^^^

Please see the main :ref:`initial` page for tips, or visit the `Cozmo SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions, or for general discussion.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
