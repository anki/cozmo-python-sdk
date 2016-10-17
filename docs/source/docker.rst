.. _docker-guide:

#####################################
Dockerized Cozmo SDK
#####################################

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

.. important:: The installation steps on this page are intended only for people that are having difficulties installing the SDK using the main Installation Guide steps.

If you have difficulties using the regular Installation Guide steps (e.g. you are using an unsupported Operating System / OS Version), then we also provide a self-contained VM (Virtual Machine) setup using Vagrant that you can install to run entirely inside VirtualBox. The steps are listed below.

To use the Cozmo SDK, the Cozmo mobile app must be installed on your mobile device and that device must be tethered to a computer via USB cable.

------------
Installation
------------

^^^^^^^^^^^^^
Prerequisites
^^^^^^^^^^^^^

* WiFi connection
* An iOS or Android mobile device with the Cozmo app installed, connected to the computer via USB cable

^^^^^^^
Install
^^^^^^^

1. Install `Docker <https://docs.docker.com/engine/installation/>`_ from the official page for your platform.
2. Install the Cozmo app on your mobile device.
3. Plug the mobile device containing the Cozmo app into your computer.
4. Run the Docker Image as::
        docker run -it --net=host -v /dev/bus/usb:/dev/bus/usb -v /tmp/.X11-unix:/tmp/.X11-unix -v `pwd`:/code -e DISPLAY=unix$DISPLAY cozmo bash
     .. important:: If using an Android device, the device will will prompt with *"Allow USB Debugging?"*. Tap **OK** to allow this option.
5. This assumes that you have downloaded the SDK examples in present working directory which can be mounted into the container at /code
6. Once everything is set up you can navigate to /code and run `./hello_world.py`
----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
