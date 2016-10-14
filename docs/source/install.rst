.. _install-guide:

##################
Installation Guide
##################

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

To use the Cozmo SDK, the Cozmo mobile app must be installed on your mobile device and that device must be tethered to a computer via USB cable.

------------
Installation
------------

^^^^^^^^^^^^^
Prerequisites
^^^^^^^^^^^^^

* Python 3.5.1 or later
* WiFi connection
* An iOS or Android mobile device with the Cozmo app installed, connected to the computer via USB cable

^^^^^^^^^^^^^^^^^^^^
SDK Example Programs
^^^^^^^^^^^^^^^^^^^^

Download SDK example programs and extract these packaged files to a new directory:

`macOS/Linux SDK Examples <http://cozmosdk.anki.com/0.7.0/cozmo_sdk_examples_0.7.0.tar.gz>`_

`Windows SDK Examples <http://cozmosdk.anki.com/0.7.0/cozmo_sdk_examples_0.7.0.zip>`_

^^^^^^^^^^^^^^
Install Python
^^^^^^^^^^^^^^

"""""
macOS
"""""

1. Install `Homebrew <http://brew.sh>`_ on your system according to the latest instructions. If you already had brew installed then update it by typing the following into your Terminal window::

    brew update

2. Once Homebrew is installed and updated, type the following into your Terminal window to install the latest version of Python 3::

    brew install python3


"""""""""""""""""""""""""""""
Linux (Ubuntu 14.04 or 16.04)
"""""""""""""""""""""""""""""

The Cozmo SDK is tested and and supported on Ubuntu 14.04 and above. While the SDK is not guaranteed to work on other versions of Linux, please ensure the following dependencies are installed if you wish to run the SDK on any other Linux system:

  * Python 3.5.1 or later
  * pip for Python 3 (Python package installer)
  * Android command line tools (https://developer.android.com/studio/index.html#Other)
  * usbmuxd for iOS

**For version 14.04 only:**

1. Type the following into your Terminal window to install Python 3.5::

    sudo add-apt-repository ppa:fkrull/deadsnakes
    sudo apt-get update
    sudo apt-get install python3.5
    sudo update-alternatives --install /usr/bin/python3 python3.5 /usr/bin/python3.5.1

2. Then install pip by typing in the following into the Terminal window::

    sudo apt-get install python3-setuptools
    sudo easy_install3 pip

3. Last, install Tkinter::

    sudo apt-get install python3.5-tk

**For Ubuntu 16.04:**

1. Type the following into your Terminal window to install Python::

    sudo apt-get update
    sudo apt-get install python3

2. Then install pip by typing in the following into the Terminal window::

    sudo apt install python3-pip

3. Last, install Tkinter::

    sudo apt-get install python3-pil.imagetk


"""""""
Windows
"""""""

1. Download the `Python 3.5.1 (or later) executable file from Python.org <https://www.python.org/downloads/>`_ and
run it on your computer. We recommend that you tick the "Add Python 3.5 to PATH" checkbox on the Setup screen.

2. To use an iOS device, install `iTunes <http://www.apple.com/itunes/download/>`_ to ensure that the usbmuxd service
is installed on your computer. Usbmuxd is required for the computer to communicate with the iOS device over a USB cable.
While iTunes needs to be installed, it does not need to be running.


^^^^^^^^^^^^^^^^^
Install Cozmo SDK
^^^^^^^^^^^^^^^^^

To install the SDK, type the following into your Command-Prompt/Terminal window::

    pip3 install --user cozmo[camera]

Note that the [camera] option adds support for processing images from Cozmo's camera.


^^^^^^^^^^^^^^^^^^^^^^^^^^
Android Debug Bridge (adb)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. important:: Android Debug Bridge (adb) MUST be installed on your computer and USB debugging MUST be enabled in order to use the SDK on an Android device.

This section sets your machine up for usage with an Android device. iOS users may skip this and proceed to the next step.

"""""
macOS
"""""

1. Type the following into a Terminal window (requires Homebrew to be installed)::

    brew install android-platform-tools

2. Enable USB Debugging on your mobile device.

    On Android devices:

      1. Tap seven (7) times on the Build Number listed under *Settings -> About Phone*.
      2. Then, under *Settings -> Developer Options*, enable USB debugging.

    On Amazon Kindle Fire:

      1. Tap seven (7) times on the Serial Number listed under *Settings -> Device Options*.
      2. Then, under *Settings -> Device Options -> Developer Options*, turn on Enable ADB.

3. After connecting your Android device to the computer via USB, in the “Allow USB Debugging?” popup, tap OK.

4. At the command line, type this command to confirm that your device shows::

      adb devices

..

At least one device should show in the result, for example::

    List of devices attached
    88148a08    device

..

"""""""""""""""""""""""""""""
Linux (Ubuntu 14.04 or 16.04)
"""""""""""""""""""""""""""""

1. If you do not yet have the Java Development Kit (JDK) version 8 installed, you must install it.

  a. To check to see if you have java installed, enter the following command into the Terminal::

        java -version

  b. If JDK version 8 is not installed, install it with the following command:

    1. On Ubuntu version 14.04::

        sudo add-apt-repository ppa:webupd8team/java
        sudo apt-get update
        sudo apt-get install oracle-java8-installer

    2. On Ubuntu 16.04::

        sudo apt install default-jre

2. Open your internet browser and go to `the Android developer website <https://developer.android.com/studio/index.html#Other>`_ .
3. Scroll down to *Get just the command line tools*. Download the SDK tools package.
4. Unzip the file into your chosen directory.
5. In the downloaded Linux SDK tools, start the Android SDK Manager by executing the program **android** in *android-sdk-linux/tools* like this::

        cd YOUR_ANDROID_SDK_LOCATION/android-sdk-linux/tools
        ./android

6. Perform the following steps in the Android SDK Manager.

  a. Deselect everything except for *Android SDK Platform - tools*. For a Nexus phone, you may also want to select *Google USB Driver* to download Google’s drivers.
  b. Click **Install**.
  c. Android Debug Bridge (adb) should now be installed to *YOUR_ANDROID_SDK_LOCATION/android-sdk-linux/platform-tools*.

7. Add adb to your PATH.

  a. Edit your `~/.bashrc` file and add this line::

        export PATH=${PATH}:YOUR_ANDROID_SDK_LOCATION/android-sdk-linux/platform-tools

  b. Save `.bashrc` and then call::

        source .bashrc

  c. Confirm that adb is in your PATH by calling the following command::

        which YOUR_ANDROID_SDK_LOCATION/android-sdk-linux/platform-tools/adb

  d. The result of this command should be::

        adb: YOUR_ANDROID_SDK_LOCATION/android-sdk-linux/platform-tools/adb

8. Enable USB Debugging on your phone.

  a. On Android devices:

      1. Tap seven (7) times on the Build Number listed under *Settings -> About Phone*.
      2. Then, under *Settings -> Developer Options*, enable USB debugging.

  b. On Amazon Kindle Fire:

      1. Tap seven (7) times on the Serial Number listed under *Settings -> Device Options*.
      2. Then, under *Settings -> Device Options -> Developer Options*, turn on **Enable ADB**.

9. After connecting your Android device to the computer via USB, in the “Allow USB Debugging?” popup, tap **OK**.
10. At the command line, type this command to confirm that your device shows::

      adb devices

..

At least one device should show in the result, for example::

    List of devices attached
    88148a08    device

..

"""""""
Windows
"""""""

1. Open your internet browser and go to `the Android developer website <https://developer.android.com/studio/index.html#Other>`_ .
2. Scroll down to *Get just the command line tools*. Download the Windows installer for the SDK tools package.
3. If you downloaded the ``.zip`` file instead of the ``.exe`` file, unzip it into your chosen directory.
4. Run the installer to start the Android SDK Tools Setup Wizard.
5. The Setup Wizard will direct you to install the Java Development Kit (JDK) from the Oracle website if you do not have it installed.
6. Complete installation of the Android SDK Tools. Take note of the directory it was installed to, such as (e.g. ``C:\Program Files (x86)\Android)``.
7. In the File Explorer, navigate to the Android SDK Tools directory noted in the previous step. Then navigate into the android-sdk child folder. From there, run the SDK Manager as Administrator by right-clicking and selecting *Run as administrator*.

  a. Deselect everything except for *Android SDK Platform - tools*. For a Nexus phone, you may also want to select *Google USB Driver* to download Google’s drivers.
  b. Click **Install**.
  c. adb should now be installed in the *platform-tools* folder.

8. Enable USB Debugging on your phone.

  a. On Android devices:

    1. Tap seven (7) times on the Build Number listed under *Settings -> About Phone*.
    2. Then, under *Settings -> Developer Options*, enable USB debugging.

  b. On Amazon Kindle Fire:

    1. Tap seven (7) times on the Serial Number listed under *Settings -> Device Options*.
    2. Then, under *Settings -> Device Options -> Developer Options*, turn on **Enable ADB**.

9. Connect your Android device to your computer via USB. When the *Allow USB Debugging?* popup displays, tap **OK**.
10. Add adb to your PATH environment variable.

  a. Right-click the Start menu and select System.
  b. Select *Advanced System Settings -> Advanced -> Environment Variables*.
  c. Under *User Variables*, select *PATH* and click **Edit**.
  d. Under *Edit Environment Variables*, click **New** and add the path to the folder containing adb (e.g. ``C:\Program Files (x86)\Android\android-sdk\platform-tools``).

11. Open a new command line window and type this command::

      adb devices

..

At least one device should show in the result, for example::

    List of devices attached
    88148a08    device

..

---------------
Troubleshooting
---------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Failure to Install Python Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your attempt to install Python packages such as NumPy fails, please upgrade your pip install as follows

    On macOS and Linux::

        pip3 install -U pip

    On Windows::

        py -3 -m pip install -U pip

    Then, retry your Python package installation.

^^^^^^^^^^^^^^^^
Cozmo SDK Forums
^^^^^^^^^^^^^^^^

Please visit the `Cozmo SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions and for general discussion.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
