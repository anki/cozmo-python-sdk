FROM ubuntu:16.04

ENV ANDROID_SDK_VERSION r24.3.3

RUN apt-get update && \
apt-get install -y -q default-jdk \
default-jre \
curl \
sudo \
wget \
python3-pip \
expect \
python3-pil \
python3-pil.imagetk && \
rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip && pip3 install numpy \
pillow \
tweepy \
flask

RUN pip3 install cozmo[camera]

RUN cd /opt && wget --output-document=android-sdk.tgz --quiet http://dl.google.com/android/android-sdk_${ANDROID_SDK_VERSION}-linux.tgz && \
  tar xzf android-sdk.tgz && \
  rm -f android-sdk.tgz && \
  chown -R root.root android-sdk-linux

RUN echo "y" | /opt/android-sdk-linux/tools/android update sdk --all --no-ui --filter platform-tools


ENV JAVA_HOME=/usr/lib/jvm/java-8-oracle
ENV ANDROID_HOME /opt/android-sdk-linux
ENV PATH ${PATH}:${ANDROID_HOME}/tools:${ANDROID_HOME}/platform-tools
