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

    brew tap caskroom/cask
    brew cask install android-platform-tools

2. Continue to :ref:`final-install` below to complete installation.

^^^^^^^^^^^^^^^^^^^^
Windows Installation
^^^^^^^^^^^^^^^^^^^^

1. In your internet browser, navigate to this `link <https://dl.google.com/android/repository/platform-tools-latest-windows.zip>`__ and download file ``platform-tools-latest-windows.zip`` to your Downloads folder.
2. Open a File Explorer window to your Downloads folder and see that your downloaded file ``platform-tools-latest-windows.zip`` is there.
3. Open a new File Explorer window and create a new folder in ``C:\Users\your_name`` named ``Android``. Then, navigate into your new Android folder. You should now be inside folder ``C:\Users\your_name\Android``.
4. Move the zip file you downloaded in step 1, ``platform-tools-latest-windows.zip``, to your new Android folder at ``C:\Users\your_name\Android``.
5. Right-click the ``platform-tools-latest-windows.zip`` file in ``C:\Users\your_name\Android`` and select Extract All.
6. With File Explorer, navigate to ``C:\Users\your_name\Android\platform-tools-latest-windows\platform-tools`` and confirm that the adb is there. You will now add this path to your PATH environment variable in the next step.
7. Add adb to your PATH environment variable.

  a. Right-click the Start menu and select *System*.
  b. Select *Advanced System Settings -> Advanced -> Environment Variables*.
  c. Under *User Variables*, select *PATH* and click **Edit**.
  d. Under *Edit Environment Variables*, click **New** and add the path to the folder containing adb (e.g. ``C:\Users\your_name\Android\platform-tools-latest-windows\platform-tools``). Click OK on all dialog boxes to confirm your change.

8. Confirm that the PATH is correctly pointing to adb.

  a. Open new a Command Prompt window. (To find the Command Prompt, you may use the search box in the lower left-hand corner of your screen.)
  b. Type ``adb`` and adb instructions should print out.

9. Continue to :ref:`final-install` below to complete installation.

^^^^^^^^^^^^^^^^^^
Linux Installation
^^^^^^^^^^^^^^^^^^

1. In your internet browser, navigate to this `link <https://dl.google.com/android/repository/platform-tools-latest-linux.zip>`__ and download file ``platform-tools-latest-linux.zip``. You may need to accept the license before downloading.
2. Navigate to the zip file download location (e.g., ~/Downloads) and extract the files. The files will be extracted to folder ``platform-tools``.
3. In your home directory, create folder ``android-sdk-linux``::

        cd ~
        mkdir android-sdk-linux

4. Move the extracted ``platform-tools`` folder to your new ``android-sdk-linux`` folder::

        mv Downloads/platform-tools android-sdk-linux

5. Confirm you see adb inside ``platform-tools``::

        cd android-sdk-linux/platform-tools
        ls adb

6. Add adb to your PATH.

  a. Edit your `~/.bashrc` file and add this line::

        export PATH=${PATH}:~/android-sdk-linux/platform-tools

  b. Save `.bashrc` and then call::

        source .bashrc

  c. Confirm that adb is in your PATH by calling the following command::

        which adb

  d. The result of this command should be the path where adb is installed.

7. Continue to :ref:`final-install` below to complete installation.


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
