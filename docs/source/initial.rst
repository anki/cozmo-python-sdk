.. _initial:

#############
Initial Setup
#############

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

To use the Cozmo SDK, the Cozmo mobile app must be installed on your mobile device and that device must be tethered to a computer via USB cable.

-------------
Prerequisites
-------------

* Python 3.5.1 or later
* WiFi connection
* An iOS or Android mobile device with the Cozmo app installed, connected to the computer via USB cable

--------------------
SDK Example Programs
--------------------

Anki provides example programs for novice and advanced users to run with the SDK. Download the SDK example programs here:

  * `macOS/Linux SDK Examples <http://cozmosdk.anki.com/0.8.0/cozmo_sdk_examples_0.8.0.tar.gz>`_

  * `Windows SDK Examples <http://cozmosdk.anki.com/0.8.0/cozmo_sdk_examples_0.8.0.zip>`_

Once downloaded, extract the packaged files to a new directory.

------------
Installation
------------

To install the SDK on your system, select the instructions for your computer's operating system.

* :ref:`install-macos`
* :ref:`install-windows`
* :ref:`install-linux`

..

.. _trouble:

---------------
Troubleshooting
---------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Failure to Install Python Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your attempt to install Python packages such as NumPy fails, please upgrade your pip install as follows:

    On macOS and Linux::

        pip3 install -U pip

    On Windows::

        py -3 -m pip install -U pip

    Once the pip command is upgraded, retry your Python package installation.

^^^^^^^^^^^^^^^^
Cozmo SDK Forums
^^^^^^^^^^^^^^^^

Please visit the `Cozmo SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions and for general discussion.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
