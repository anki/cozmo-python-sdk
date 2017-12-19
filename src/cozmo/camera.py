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
sending, enable/disable color images, modify various camera settings,
read the robot's unique camera calibration settings, as well as observe
raw unprocessed images being sent by the robot.

Generally, however, it is more useful to observe
:class:`cozmo.world.EvtNewCameraImage` events, which include the raw camera
images along with annotated images, which can illustrate objects the robot
has identified.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['EvtNewRawCameraImage', 'EvtRobotObservedMotion', 'CameraConfig', 'Camera']

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
from . import util

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


class EvtRobotObservedMotion(event.Event):
    '''Generated when the robot observes motion.'''
    timestamp = "Robot timestamp for when movement was observed"

    img_area = "Area of the supporting region for the point, as a fraction of the image"
    img_pos = "Centroid of observed motion, relative to top-left corner"

    ground_area = "Area of the supporting region for the point, as a fraction of the ground ROI"
    ground_pos = "Approximate coordinates of observed motion on the ground, relative to robot, in mm"

    has_top_movement = "Movement detected near the top of the robot's view"
    top_img_pos = "Coordinates of the centroid of observed motion, relative to top-left corner"

    has_left_movement = "Movement detected near the left edge of the robot's view"
    left_img_pos = "Coordinates of the centroid of observed motion, relative to top-left corner"

    has_right_movement = "Movement detected near the right edge of the robot's view"
    right_img_pos = "Coordinates of the centroid of observed motion, relative to top-left corner"


class CameraConfig:
    """The fixed properties for Cozmo's Camera

    A full 3x3 calibration matrix for doing 3D reasoning based on the camera
    images would look like:

        +--------------+--------------+---------------+
        |focal_length.x|      0       |    center.x   |
        +--------------+--------------+---------------+
        |       0      |focal_length.y|    center.y   |
        +--------------+--------------+---------------+
        |       0      |       0      |        1      |
        +--------------+--------------+---------------+
    """

    def __init__(self,
                 focal_length_x: float,
                 focal_length_y: float,
                 center_x: float,
                 center_y: float,
                 fov_x_degrees: float,
                 fov_y_degrees: float,
                 min_exposure_time_ms: int,
                 max_exposure_time_ms: int,
                 min_gain: float,
                 max_gain: float):
        self._focal_length = util.Vector2(focal_length_x, focal_length_y)
        self._center = util.Vector2(center_x, center_y)
        self._fov_x = util.degrees(fov_x_degrees)
        self._fov_y = util.degrees(fov_y_degrees)
        self._min_exposure_time_ms = min_exposure_time_ms
        self._max_exposure_time_ms = max_exposure_time_ms
        self._min_gain = min_gain
        self._max_gain = max_gain

    @classmethod
    def _create_from_clad(cls, cs):
        return cls(cs.focalLengthX, cs.focalLengthY,
                   cs.centerX, cs.centerY,
                   cs.fovX, cs.fovY,
                   cs.minCameraExposureTime_ms, cs.maxCameraExposureTime_ms,
                   cs.minCameraGain, cs.maxCameraGain)

    # Fixed camera properties (calibrated for each robot at the factory).

    @property
    def focal_length(self):
        ''':class:`cozmo.util.Vector2`: The focal length of the camera.

        This is focal length combined with pixel skew (as the pixels aren't
        perfectly square), so there are subtly different values for x and y.
        It is in floating point pixel values e.g. <288.87, 288.36>.
        '''
        return self._focal_length

    @property
    def center(self):
        ''':class:`cozmo.util.Vector2`: The focal center of the camera.

        This is the position of the optical center of projection within the
        image. It will be close to the center of the image, but adjusted based
        on the calibration of the lens at the factory. It is in floating point
        pixel values e.g. <155.11, 111.40>.
        '''
        return self._center

    @property
    def fov_x(self):
        ''':class:`cozmo.util.Angle`: The x (horizontal) field of view.'''
        return self._fov_x

    @property
    def fov_y(self):
        ''':class:`cozmo.util.Angle`: The y (vertical) field of view.'''
        return self._fov_y

    # The fixed range of values supported for this camera.

    @property
    def min_exposure_time_ms(self):
        '''int: The minimum supported exposure time in milliseconds.'''
        return self._min_exposure_time_ms

    @property
    def max_exposure_time_ms(self):
        '''int: The maximum supported exposure time in milliseconds.'''
        return self._max_exposure_time_ms

    @property
    def min_gain(self):
        '''float: The minimum supported camera gain.'''
        return self._min_gain

    @property
    def max_gain(self):
        '''float: The maximum supported camera gain.'''
        return self._max_gain


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
        self._color_image_enabled = None
        self._config = None  # type: CameraConfig
        self._gain = 0.0
        self._exposure_ms = 0
        self._auto_exposure_enabled = True

        if np is None:
            logger.warning("Camera image processing not available due to missing NumPy or Pillow packages: %s" % _img_processing_available)
        else:
            # set property to ensure clad initialization is sent.
            self.image_stream_enabled = False
            self.color_image_enabled = False
        self._reset_partial_state()

    def enable_auto_exposure(self, enable_auto_exposure = True):
        '''Enable auto exposure on Cozmo's Camera.

        Enable auto exposure on Cozmo's camera to constantly update the exposure
        time and gain values based on the recent images. This is the default mode
        when any SDK program starts.

        Args:
            enable_auto_exposure (bool): whether the camera should automcatically adjust exposure
        '''
        msg = _clad_to_engine_iface.SetCameraSettings(enableAutoExposure = enable_auto_exposure)
        self.robot.conn.send_msg(msg)

    def set_manual_exposure(self, exposure_ms, gain):
        '''Set manual exposure values for Cozmo's Camera.

        Disable auto exposure on Cozmo's camera and force the specified exposure
        time and gain values.

        Args:
            exposure_ms (int): The desired exposure time in milliseconds.
                Must be within the robot's
                :attr:`~cozmo.camera.Camera.config` exposure range from
                :attr:`~cozmo.camera.CameraConfig.min_exposure_time_ms` to
                :attr:`~cozmo.camera.CameraConfig.max_exposure_time_ms`
            gain (float): The desired gain value.
                Must be within the robot's
                :attr:`~cozmo.camera.Camera.camera_config` gain range from
                :attr:`~cozmo.camera.CameraConfig.min_gain` to
                :attr:`~cozmo.camera.CameraConfig.max_gain`

        Raises:
            :class:`ValueError` if supplied an out-of-range exposure or gain.
        '''
        cam = self.config

        if (exposure_ms < cam.min_exposure_time_ms) or (exposure_ms > cam.max_exposure_time_ms):
            raise ValueError('exposure_ms %s out of range %s..%s' %
                             (exposure_ms, cam.min_exposure_time_ms, cam.max_exposure_time_ms))

        if (gain < cam.min_gain) or (gain > cam.max_gain):
            raise ValueError('gain %s out of range %s..%s' %
                             (gain, cam.min_gain, cam.max_gain))

        msg = _clad_to_engine_iface.SetCameraSettings(enableAutoExposure=False,
                                                      exposure_ms=exposure_ms,
                                                      gain=gain)
        self.robot.conn.send_msg(msg)

    #### Private Methods ####

    def _reset_partial_state(self):
        self._partial_data = None
        self._partial_image_id = None
        self._partial_invalid = False
        self._partial_size = 0
        self._partial_metadata = None
        self._last_chunk_id = -1

    def _set_config(self, clad_config):
        self._config = CameraConfig._create_from_clad(clad_config)

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

        msg = _clad_to_engine_iface.ImageRequest(mode=image_send_mode)

        self.robot.conn.send_msg(msg)

    @property
    @_require_img_processing
    def color_image_enabled(self):
        '''bool: Set to true to receive color images from the robot.'''
        if np is None:
            return False

        return self._color_image_enabled

    @color_image_enabled.setter
    @_require_img_processing
    def color_image_enabled(self, enabled):
        if self._color_image_enabled == enabled:
            return

        self._color_image_enabled = enabled

        msg = _clad_to_engine_iface.EnableColorImages(enable = enabled)
        self.robot.conn.send_msg(msg)

    @property
    def config(self):
        ''':class:`cozmo.camera.CameraConfig`: The read-only config/calibration for the camera'''
        return self._config

    @property
    def is_auto_exposure_enabled(self):
        '''bool: True if auto exposure is currently enabled

        If auto exposure is enabled the `gain` and `exposure_ms`
        values will constantly be updated by Cozmo.
        '''
        return self._auto_exposure_enabled

    @property
    def gain(self):
        '''float: The current camera gain setting.'''
        return self._gain

    @property
    def exposure_ms(self):
        '''int: The current camera exposure setting in milliseconds.'''
        return self._exposure_ms

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

    def _recv_msg_current_camera_params(self, evt, *, msg):
        self._gain = msg.cameraGain
        self._exposure_ms = msg.exposure_ms
        self._auto_exposure_enabled = msg.autoExposureEnabled

    def _recv_msg_robot_observed_motion(self, evt, *, msg):
        self.dispatch_event(EvtRobotObservedMotion,
                            timestamp=msg.timestamp,
                            img_area=msg.img_area,
                            img_pos=util.Vector2(msg.img_x, msg.img_y),
                            ground_area=msg.ground_area,
                            ground_pos=util.Vector2(msg.ground_x, msg.ground_y),
                            has_top_movement=(msg.top_img_area > 0),
                            top_img_pos=util.Vector2(msg.top_img_x, msg.top_img_y),
                            has_left_movement=(msg.left_img_area > 0),
                            left_img_pos=util.Vector2(msg.left_img_x, msg.left_img_y),
                            has_right_movement=(msg.right_img_area > 0),
                            right_img_pos=util.Vector2(msg.right_img_x, msg.right_img_y))

    def _process_completed_image(self):
        data = self._partial_data[0:self._partial_size]
        
        # The first byte of the image is whether or not it is in color
        is_color_image = data[0] != 0
        
        if self._partial_metadata.imageEncoding ==  _clad_to_game_cozmo.ImageEncoding.JPEGMinimizedGray:
            width, height = RESOLUTIONS[self._partial_metadata.resolution]
            
            if is_color_image:
                # Color images are half width
                width = width // 2
                data = _minicolor_to_jpeg(data, width, height)
            else:
                data = _minigray_to_jpeg(data, width, height)
                
        image = Image.open(io.BytesIO(data)).convert('RGB')

        # Color images need to be resized to the proper resolution
        if is_color_image:
            size = RESOLUTIONS[self._partial_metadata.resolution]
            image = image.resize(size)
        
        self._latest_image = image
        self.dispatch_event(EvtNewRawCameraImage, image=image)


    #### Public Event Handlers ####


@_require_img_processing
def _minigray_to_jpeg(minigray, width, height):
        "Converts miniGrayToJpeg format to normal jpeg format"
        #This should be 'exactly' what is done in the miniGrayToJpeg function in encodedImage.cpp
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
        
        return _mini_to_jpeg_helper(minigray, width, height, header50)

@_require_img_processing
def _minicolor_to_jpeg(minicolor, width, height):
        "Converts miniColorToJpeg format to normal jpeg format"
        #This should be 'exactly' what is done in the miniColorToJpeg function in encodedImage.cpp
        header = np.array([
             0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
             0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0x10, 0x0B, 0x0C, 0x0E, 0x0C, 0x0A, 0x10, # 0x19 = QTable
             0x0E, 0x0D, 0x0E, 0x12, 0x11, 0x10, 0x13, 0x18, 0x28, 0x1A, 0x18, 0x16, 0x16, 0x18, 0x31, 0x23,
             0x25, 0x1D, 0x28, 0x3A, 0x33, 0x3D, 0x3C, 0x39, 0x33, 0x38, 0x37, 0x40, 0x48, 0x5C, 0x4E, 0x40,
             0x44, 0x57, 0x45, 0x37, 0x38, 0x50, 0x6D, 0x51, 0x57, 0x5F, 0x62, 0x67, 0x68, 0x67, 0x3E, 0x4D,
             0x71, 0x79, 0x70, 0x64, 0x78, 0x5C, 0x65, 0x67, 0x63, 0xFF, 0xC0, 0x00, 17, # 8+3*components
             0x08, 0x00, 0xF0, # 0x5E = Height x Width
             0x01, 0x40,
             0x03, # 3 components
             0x01, 0x21, 0x00, # Y 2x1 res
             0x02, 0x11, 0x00, # Cb
             0x03, 0x11, 0x00, # Cr
             0xFF, 0xC4, 0x00, 0xD2, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
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
             0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA,
             0xFF, 0xDA, 0x00, 12,
             0x03, # 3 components
             0x01, 0x00, # Y
             0x02, 0x00, # Cb same AC/DC
             0x03, 0x00, # Cr same AC/DC
             0x00, 0x3F, 0x00
            ], dtype=np.uint8)

        return _mini_to_jpeg_helper(minicolor, width, height, header)

@_require_img_processing
def _mini_to_jpeg_helper(mini, width, height, header):
        bufferIn = mini.tolist()
        currLen = len(mini)

        headerLength = len(header)
        # For worst case expansion
        bufferOut = np.array([0] * (currLen*2 + headerLength), dtype=np.uint8)

        for i in range(headerLength):
            bufferOut[i] = header[i]

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
