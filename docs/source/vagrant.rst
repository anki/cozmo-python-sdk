.. _vagrant-guide:

#####################################
Alternate Install via Virtual Machine
#####################################

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

.. important:: The installation steps on this page are intended only for people that are having difficulties installing the SDK using the main Installation Guide steps.

If you have difficulties using the regular Installation Guide steps (e.g. you are using an unsupported Operating System / OS Version), then we also provide a self-contained VM (Virtual Machine) setup using Vagrant that you can install to run entirely inside VirtualBox. The steps are listed below.

To use the Cozmo SDK, the Cozmo mobile app must be installed on your mobile device and that device must be tethered to a computer via USB cable.

^^^^^^^^^^^^
Installation
^^^^^^^^^^^^

"""""""""""""
Prerequisites
"""""""""""""

* WiFi connection
* An iOS or Android mobile device with the Cozmo app installed, connected to the computer via USB cable

"""""""
Install
"""""""

1. Install `VirtualBox and the VirtualBox Extension Pack <https://www.virtualbox.org/wiki/Downloads>`_ from the official webpage. Both of these *must* be installed in order for Vagrant to work properly.
2. Install `Vagrant <https://www.vagrantup.com/downloads.html>`_ from the official webpage.
3. Install the Cozmo app on your mobile device.
4. Plug the mobile device containing the Cozmo app into your computer.
5. For **Windows**:

  a. Download :verlink:`vagrant_bundle_0.0.0.zip <vagrant_bundle_0.0.0.zip>`.
  b. Unzip the ``vagrant_bundle_***.zip`` file into a folder of your choosing.
  c. Open a Command Prompt window.

    1. Enter the following commands::

        cd (location you extracted the .zip file)
        cd vagrant_bundle

    2. Enter the following command::

        vagrant up

    .. important:: Wait for `vagrant up` to completely finish before continuing to the next step.

  d. Navigate to where the Virtual Machine is currently running.

  .. raw:: html

    <blockquote>
    <div><div class="admonition note">
    <p class="first admonition-title">Note</p>
    <p class="last">The Virtual Machine is set up with the following credentials:
    <br><br>user - vagrant
    <br>password - vagrant</p>
    </div>
    </div></blockquote>

  |

  e. Within the VM, open xterm. Once xterm is open, run the following commands in order. Please wait for each command to finish before entering the next one. This step may take several minutes. ::

      /vagrant/setup-vm.sh

    .. important:: Be sure to accept the Android SDK license prompt before continuing.
    .. important:: If using an Android device, the device will will prompt with *"Allow USB Debugging?"*. Tap **OK** to allow this option.

    .. code-block:: python

      cd /vagrant/cozmo_sdk_examples_***

..

6. For **macOS/Linux**:

  a. Download :verlink:`vagrant_bundle_0.0.0.tar.gz <vagrant_bundle_0.0.0.tar.gz>`.
  b. Open a Terminal window.

    1. Enter the following commands::

        cd (location you downloaded the vagrant_bundle_***.tar.gz file)
        tar -xzf vagrant_bundle_***.tar.gz
        cd vagrant_bundle

    2. Enter the following command::

        vagrant up

    .. important:: Wait for `vagrant up` to completely finish before continuing to the next step.

  d. Navigate to where the Virtual Machine is currently running.

  .. raw:: html

    <blockquote>
    <div><div class="admonition note">
    <p class="first admonition-title">Note</p>
    <p class="last">The Virtual Machine is set up with the following credentials:
    <br><br>user - vagrant
    <br>password - vagrant</p>
    </div>
    </div></blockquote>

  |

  e. Within the VM, open xterm. Once xterm is open, run the following commands in order. Please wait for each command to finish before entering the next one. This step may take several minutes. ::

        /vagrant/setup-vm.sh

    .. important:: Be sure to accept the Android SDK license prompt before continuing.

    .. important:: If using an Android device, the device will will prompt with *"Allow USB Debugging?"*. Tap **OK** to allow this option.

    .. code-block:: python

        cd /vagrant/cozmo_sdk_examples_***

7. Make sure Cozmo is powered on and charged. Connect to the Cozmo robot's WiFi from the mobile device and then connect to the Cozmo robot within the app.
8. Enter SDK mode on the app.

    a. On the Cozmo app, tap the gear icon at the top right corner to open the Settings menu.
    b. Swipe left to show the Cozmo SDK option and tap the **Enable SDK** button.

9. To run a program enter the following into the virtual machine's Terminal prompt::

        ./program_name.py

For example, to run the Hello World example program, you would type ``./hello_world.py``.

.. important:: You must either relaunch with "vagrant up" or save your virtual machine's state when shutting down.  Otherwise the /vagrant/ folder on the virtual machine will be empty on subsequent runs.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
