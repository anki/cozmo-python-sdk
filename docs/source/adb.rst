.. _adb:

####################
Android Debug Bridge
####################

.. important:: Android Debug Bridge (adb) is required ONLY for those users pairing an Android mobile device with Cozmo.

Android Debug Bridge (adb) is necessary in order for the Cozmo SDK to work with Android mobile devices. Please ensure adb is installed before attempting to run the Cozmo SDK with a paired Android device.

^^^^^^^^^^^^^^^^^^
macOS Installation
^^^^^^^^^^^^^^^^^^

1. Type the following into a Terminal window (requires Homebrew to be installed)::

    brew install android-platform-tools

2. Continue to :ref:`final-install` below to complete installation.

^^^^^^^^^^^^^^^^^^^^
Windows Installation
^^^^^^^^^^^^^^^^^^^^

1. Open your internet browser and go to the `Android developer website. <https://developer.android.com/studio/index.html#downloads>`_
2. Scroll down to *Get just the command line tools*. Download the Windows zip file for the SDK tools package, taking note of where the file is downloaded.
3. In the File Explorer, create a new folder in ``C:\Users\your_name`` named ``Android``. Then, navigate into your new Android folder. You should now be inside folder ``C:\Users\your_name\Android``.
4. Move the zip file you downloaded in step 2 to your new Android folder at ``C:\Users\your_name\Android``.
5. Right-click the zip file in ``C:\Users\your_name\Android`` and select Extract All.
6. Open a Command Prompt window. (To find the Command Prompt, you may use the search box in the lower left-hand corner of your screen.) In the Command Prompt window, navigate to your Android folder by typing ``cd C:\Users\your_name\Android``.
7. Next, navigate to the ``android`` (or ``android.bat``) file inside the SDK tools package by typing this command: ``cd tools_r*-windows\tools`` (where ``r*`` is the version of your tools download file, e.g. ``tools_r25.2.3-windows``).

8. Finally, run this command: ``android``
  a. If you do not have Java installed, instructions will display in your Command Prompt window to tell you how to install it. Follow the instructions to install Java 8. Once Java 8 is installed, run the ``android`` command again.
  b. The Android SDK Manager window will display. In the window, deselect everything except for *Android SDK Platform-tools*.
  c. Click **Install 1 Package**, accept the license and click **Install**.
  d. Take note of the SDK Path displayed in the upper left corner of the Android SDK Manager window (e.g., ``C:\Users\your_name\Android\tools_r25.2.3-windows``).

  NOTE: If you are unable to install due to a permissions error, then return to File Explorer, navigate to ``C:\Users\your_name\Android\tools_r*-windows\tools\``, right click ``android`` and select *Run as administrator*. Then repeat steps 9b-d.

9. With File Explorer, check that you can find the adb file in ``C:\Users\your_name\Android\tools_r*-windows\tools\platform-tools``. You will now add this path to your PATH environment variable in the next step.

10. Add adb to your PATH environment variable.

  a. Right-click the Start menu and select *System*.
  b. Select *Advanced System Settings -> Advanced -> Environment Variables*.
  c. Under *User Variables*, select *PATH* and click **Edit**.
  d. Under *Edit Environment Variables*, click **New** and add the path to the folder containing adb (e.g. ``C:\Users\your_name\Android\tools_r25.2.3-windows\tools\platform-tools``).

11. Continue to :ref:`final-install` below to complete installation.

^^^^^^^^^^^^^^^^^^
Linux Installation
^^^^^^^^^^^^^^^^^^

1. If you do not yet have the Java Development Kit (JDK) version 8 installed, you must install it.

  a. To check to see if you have Java installed, enter the following command into the Terminal::

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
5. In the downloaded Linux SDK tools, start the Android SDK Manager by executing the program **android** in ``android-sdk-linux/tools`` like this::

        cd YOUR_ANDROID_SDK_LOCATION/android-sdk-linux/tools
        ./android

6. Perform the following steps in the Android SDK Manager.

  a. Deselect everything except for *Android SDK Platform - tools*.
  b. Click **Install** once finished.
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

8. Continue to :ref:`final-install` below to complete installation.


.. _final-install:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Final Installation (All Platforms)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Enable USB Debugging on your phone.

  a. On Android devices:

    1. Tap seven (7) times on the Build Number listed under *Settings -> About Phone*.
    2. Then, under *Settings -> Developer Options*, enable USB debugging.

  b. On Amazon Kindle Fire:

    1. Tap seven (7) times on the Serial Number listed under *Settings -> Device Options*.
    2. Then, under *Settings -> Device Options -> Developer Options*, turn on Enable ADB.

2. Connect your Android device to your computer via USB. When the *Allow USB Debugging?* popup displays, tap **OK**.
3. At the command line, type this command to confirm that your device shows::

      adb devices

..

  At least one device should show in the result, for example::

      List of devices attached
      88148a08    device

  If you are required to accept the connection request on the mobile device itself, a message will appear saying the device is unauthorized. For example::

      List of devices attached
      88148a08 unauthorized
