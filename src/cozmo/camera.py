# Copyright (c) 2016 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Support for Cozmo's camera.

Cozmo has a built-in camera which he uses to observe the world around him.

The :class:`Camera` class defined in this module is made available as
:attr:`cozmo.world.World.camera` and can be used to enable/disable image
sending as well as observe raw unprocessed images being sent by the robot.

Generally, however, it is more useful to observe
:class:`cozmo.world.EvtNewCameraImage` events, which include the raw camera
images along with annotated images, which can illustrate objects the robot
has identified.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['EvtNewRawCameraImage', 'Camera']

import functools
import io

_img_processing_available = True

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:
    np = None
    _img_processing_available = exc


from . import event
from . import logger

from ._clad import _clad_to_engine_iface, _clad_to_engine_cozmo, _clad_to_game_cozmo


_clad_res = _clad_to_game_cozmo.ImageResolution
RESOLUTIONS = {
    _clad_res.VerificationSnapshot: (16, 16),
    _clad_res.QQQQVGA: (40, 30),
    _clad_res.QQQVGA: (80, 60),
    _clad_res.QQVGA: (160, 120),
    _clad_res.QVGA: (320, 240),
    _clad_res.CVGA: (400, 296),
    _clad_res.VGA: (640, 480),
    _clad_res.SVGA: (800, 600),
    _clad_res.XGA: (1024, 768),
    _clad_res.SXGA: (1280, 960),
    _clad_res.UXGA: (1600, 1200),
    _clad_res.QXGA: (2048, 1536),
    _clad_res.QUXGA: (3200, 2400)
}


# wrap functions/methods that require NumPy or PIL with this
# decorator to ensure they fail with a useful error if those packages
# are not loaded.
def _require_img_processing(f):
    @functools.wraps(f)
    def wrapper(*a, **kw):
        if _img_processing_available is not True:
            raise ImportError("Camera image processing not available: %s" % _img_processing_available)
        return f(*a, **kw)
    return wrapper


class EvtNewRawCameraImage(event.Event):
    '''Dispatched when a new raw image is received from the robot's camera.

    See also :class:`~cozmo.world.EvtNewCameraImage` which provides access
    to both the raw image and a scaled and annotated version.
    '''
    image = 'A PIL.Image.Image object'


class Camera(event.Dispatcher):
    '''Represents Cozmo's camera.

    The Camera object receives images from Cozmo's camera and emits
    EvtNewRawCameraImage events.

    The :class:`cozmo.world.World` instance observes the camera and provides
    more useful methods for accessing the camera images.

    .. important::
        The camera will not receive any image data unless you
        explicitly enable it by setting :attr:`Camera.image_stream_enabled`
        to ``True``
    '''

    def __init__(self, robot, **kw):
        super().__init__(**kw)
        self.robot = robot
        self._image_stream_enabled = None
        if np is None:
            logger.warn("Camera image processing not available due to missng NumPy or Pillow packages: %s" % _img_processing_available)
        else:
            # set property to ensure clad initialization is sent.
            self.image_stream_enabled = False
        self._reset_partial_state()


    #### Private Methods ####

    def _reset_partial_state(self):
        self._partial_data = None
        self._partial_image_id = None
        self._partial_invalid = False
        self._partial_size = 0
        self._partial_metadata = None
        self._last_chunk_id = -1

    #### Properties ####

    @property
    @_require_img_processing
    def image_stream_enabled(self):
        '''bool: Set to true to receive camera images from the robot.'''
        if np is None:
            return False

        return self._image_stream_enabled

    @image_stream_enabled.setter
    @_require_img_processing
    def image_stream_enabled(self, enabled):
        if self._image_stream_enabled == enabled:
            return

        self._image_stream_enabled = enabled

        if enabled:
            image_send_mode = _clad_to_engine_cozmo.ImageSendMode.Stream
        else:
            image_send_mode = _clad_to_engine_cozmo.ImageSendMode.Off

        msg = _clad_to_engine_iface.ImageRequest(
                robotID=self.robot.robot_id, mode=image_send_mode)

        self.robot.conn.send_msg(msg)


    #### Private Event Handlers ####

    def _recv_msg_image_chunk(self, evt, *, msg):
        if np is None:
            return
        if self._partial_image_id is not None and msg.chunkId == 0:
            if not self._partial_invalid:
                logger.debug("Lost final chunk of image; discarding")
            self._partial_image_id = None

        if self._partial_image_id is None:
            if msg.chunkId != 0:
                if not self._partial_invalid:
                    logger.debug("Received chunk of broken image")
                self._partial_invalid = True
                return
            # discard any previous in-progress image
            self._reset_partial_state()
            self._partial_image_id = msg.imageId
            self._partial_metadata = msg

            max_size = msg.imageChunkCount * _clad_to_game_cozmo.ImageConstants.IMAGE_CHUNK_SIZE
            width, height = RESOLUTIONS[msg.resolution]
            max_size = width * height * 3 # 3 bytes (RGB) per pixel
            self._partial_data = np.empty(max_size, dtype=np.uint8)

        if msg.chunkId != (self._last_chunk_id + 1) or msg.imageId != self._partial_image_id:
            logger.debug("Image missing chunks; discarding (last_chunk_id=%d partial_image_id=%s)",
                    self._last_chunk_id, self._partial_image_id)
            self._reset_partial_state()
            self._partial_invalid = True
            return

        offset = self._partial_size
        self._partial_data[offset:offset+len(msg.data)] = msg.data
        self._partial_size += len(msg.data)
        self._last_chunk_id = msg.chunkId

        if msg.chunkId == (msg.imageChunkCount - 1):
            self._process_completed_image()
            self._reset_partial_state()

    def _process_completed_image(self):
        data = self._partial_data[0:self._partial_size]
        if self._partial_metadata.imageEncoding ==  _clad_to_game_cozmo.ImageEncoding.JPEGMinimizedGray:
            width, height = RESOLUTIONS[self._partial_metadata.resolution]
            data = _minigray_to_jpeg(data, width, height)
        image = Image.open(io.BytesIO(data)).convert('RGB')
        self._latest_image = image
        self.dispatch_event(EvtNewRawCameraImage, image=image)


    #### Public Event Handlers ####


@_require_img_processing
def _minigray_to_jpeg(minigray,  width, height):
        "Converts miniGrayToJpeg format to normal jpeg format"
        # Does not work correctly yet
        bufferIn = minigray.tolist()
        currLen = len(bufferIn)
        #This should be 'exactly' what is done in the miniGrayToJpeg function in ImageDeChunker.cpp
        header50 = np.array([
              0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
              0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0x10, 0x0B, 0x0C, 0x0E, 0x0C, 0x0A, 0x10, #// 0x19 = QTable
              0x0E, 0x0D, 0x0E, 0x12, 0x11, 0x10, 0x13, 0x18, 0x28, 0x1A, 0x18, 0x16, 0x16, 0x18, 0x31, 0x23,
              0x25, 0x1D, 0x28, 0x3A, 0x33, 0x3D, 0x3C, 0x39, 0x33, 0x38, 0x37, 0x40, 0x48, 0x5C, 0x4E, 0x40,
              0x44, 0x57, 0x45, 0x37, 0x38, 0x50, 0x6D, 0x51, 0x57, 0x5F, 0x62, 0x67, 0x68, 0x67, 0x3E, 0x4D,

              #//0x71, 0x79, 0x70, 0x64, 0x78, 0x5C, 0x65, 0x67, 0x63, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0xF0, #// 0x5E = Height x Width
              0x71, 0x79, 0x70, 0x64, 0x78, 0x5C, 0x65, 0x67, 0x63, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x01, 0x28, #// 0x5E = Height x Width

              #//0x01, 0x40, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0xD2, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
              0x01, 0x90, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0xD2, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,

              0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
              0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x10, 0x00, 0x02, 0x01, 0x03, 0x03, 0x02, 0x04, 0x03,
              0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D, 0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
              0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
              0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16,
              0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
              0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
              0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
              0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
              0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
              0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4,
              0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA,
              0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
              0x00, 0x00, 0x3F, 0x00
            ], dtype=np.uint8)
        headerLength = len(header50)
        # For worst case expansion
        bufferOut = np.array([0] * (currLen*2 + headerLength), dtype=np.uint8)

        for i in range(headerLength):
            bufferOut[i] = header50[i]

        bufferOut[0x5e] = height >> 8
        bufferOut[0x5f] = height & 0xff
        bufferOut[0x60] = width  >> 8
        bufferOut[0x61] = width  & 0xff
        # Remove padding at the end
        while (bufferIn[currLen-1] == 0xff):
            currLen -= 1

        off = headerLength
        for i in range(currLen-1):
            bufferOut[off] = bufferIn[i+1]
            off += 1
            if (bufferIn[i+1] == 0xff):
                bufferOut[off] = 0
                off += 1

        bufferOut[off] = 0xff
        off += 1
        bufferOut[off] = 0xD9

        bufferOut[:off]
        return np.asarray(bufferOut)
