#!/usr/bin/env bash

echo ">>> Updating apt-get"
sudo apt-get -y -q update

echo ">>> Installing Dependencies"
sudo apt-get -y -q install default-jdk \
default-jre \
curl \
python3-pip \
expect \
python3-pil \
python3-pil.imagetk \
freeglut3
pip3 install numpy \
pillow \
tweepy \
flask \
PyOpenGL \
PyOpenGL-accelerate
sudo localectl set-locale LANG="en_US.UTF-8"

echo ">>> Installing Android Command Line Tools"
curl -o /tmp/android-sdk_r24.4.1-linux.tgz https://dl.google.com/android/android-sdk_r24.4.1-linux.tgz
tar -xzf /tmp/android-sdk_r24.4.1-linux.tgz -C /home/vagrant
sudo chown -R vagrant /home/vagrant/android-sdk-linux/
echo "ANDROID_HOME=~/android-sdk-linux" >> /home/vagrant/.bashrc
echo "export JAVA_HOME=/usr/lib/jvm/java-8-oracle" >> /home/vagrant/.bashrc
echo "PATH=\$PATH:~/android-sdk-linux/tools:~/android-sdk-linux/platform-tools" >> /home/vagrant/.bashrc

echo ">>> Installing SDK Android 24"
/home/vagrant/android-sdk-linux/tools/android update sdk -u --all --filter platform-tool

echo ">>> Extracting Cozmo SDK"
pushd /vagrant
tar -xzf cozmo_sdk_examples.tar.gz
popd
pip3 install cozmo[camera]

echo ">>> Turn Screensaver Lock OFF"
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false

exec bash
