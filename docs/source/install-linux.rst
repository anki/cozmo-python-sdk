.. _install-linux:

####################
Installation - Linux
####################

This guide provides instructions on installing the Cozmo SDK for computers running with an Ubuntu Linux operating system.

.. warning:: The Cozmo SDK is tested and and supported on Ubuntu 14.04 and 16.04. Anki makes no guarantee the Cozmo SDK will work on other versions of Linux.  If you wish to try the Cozmo SDK on versions of Linux *other than* Ubuntu 14.04 or 16.04, please ensure the following dependencies are installed:

  * Python 3.5.1 or later
  * pip for Python 3 (Python package installer)
  * Android command-line tools (https://developer.android.com/studio/index.html#Other)
  * usbmuxd for iOS / :ref:`adb` for Android


^^^^^^^^^^^^
Ubuntu 14.04
^^^^^^^^^^^^

"""""""""""""""""""
Python Installation
"""""""""""""""""""

1. Type the following into your Terminal window to install Python 3.5::

    sudo add-apt-repository ppa:deadsnakes
    sudo apt-get update
    sudo apt-get install python3.5 python3.5-tk

2. Then, install and set up virtualenv::

    sudo apt-get install python-pip
    pip install virtualenv
    virtualenv -p python3.5 ~/cozmo-env

3. Last, make sure to activate the virtualenv any time you use cozmo::

    source ~/cozmo-env/bin/activate

.. note:: You'll need to activate the virtualenv before running any python or pip commands.  Learn more about virtualenv `here <https://virtualenv.pypa.io/en/stable/userguide/>`_.

""""""""""""""""
SDK Installation
""""""""""""""""

To install the SDK, type the following into the Terminal window::

    pip install 'cozmo[camera]'

Note that the [camera] option adds support for processing images from Cozmo's camera.

"""""""""""
SDK Upgrade
"""""""""""

To upgrade the SDK from a previous install, enter this command::

    pip install --upgrade cozmo

^^^^^^^^^^^^
Ubuntu 16.04
^^^^^^^^^^^^

"""""""""""""""""""
Python Installation
"""""""""""""""""""

1. Type the following into your Terminal window to install Python::

    sudo apt-get update
    sudo apt-get install python3

2. Then install pip by typing in the following into the Terminal window::

    sudo apt install python3-pip

3. Last, install Tkinter::

    sudo apt-get install python3-pil.imagetk

""""""""""""""""
SDK Installation
""""""""""""""""

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

* **iOS** devices require `usbmuxd <https://github.com/libimobiledevice/usbmuxd>`_ in order to run the Cozmo SDK. Usbmuxd is required for the computer to communicate with the iOS device over a USB cable.

* **Android** devices require installation of :ref:`adb` (adb) in order to run the Cozmo SDK. This is required for the computer to communicate with the Android mobile device over a USB cable and runs automatically when required.

^^^^^^^^^^^^^^^
Troubleshooting
^^^^^^^^^^^^^^^

Please see the :ref:`trouble` section of the Initial Setup page for tips, or visit the `Cozmo SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions, or for general discussion.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
