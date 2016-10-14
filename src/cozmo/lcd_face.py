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

''' Cozmo's LCD-screen that displays his face - related functions and values.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['dimensions', 'convert_pixels_to_screen_data',
           'convert_image_to_screen_data']


SCREEN_WIDTH = 128
SCREEN_HALF_HEIGHT = 32
SCREEN_HEIGHT = SCREEN_HALF_HEIGHT * 2


def dimensions():
    '''Return the dimension (width, height) of the lcd screen.

    Note: The screen is displayed interlaced, with only every other line displayed
    This alternates every time the image is changed (no longer than 30 seconds)
    to prevent screen burn-in. Therefore to ensure the image looks correct on
    either scan-line offset we use half the vertical resolution

    Returns:
        A tuple of ints (width, height)
    '''
    return SCREEN_WIDTH, SCREEN_HALF_HEIGHT


def convert_pixels_to_screen_data(pixel_data, image_width, image_height):
    '''Convert a sequence of pixel data to the correct format to display on Cozmo's face.

    Args:
        pixel_data (:class:`bytes`): sequence of pixel values, should be in binary (1s or 0s)
        image_width (int): width of the image defined by the pixel_data
        image_height (int): height of the image defined by the pixel_data

    Returns:
        A :class:`bytearray` object representing all of the pixels (8 pixels packed per byte)

    Raises:
        ValueError: Invalid Dimensions
        ValueError: Bad image_width
        ValueError: Bad image_height
    '''

    if len(pixel_data) != (image_width * image_height):
        raise ValueError('Invalid Dimensions: len(pixel_data) {0} != image_width={1} * image_height={2} (== {3})'.
            format(len(pixel_data), image_width, image_height, image_width * image_height))

    num_columns_per_pixel = int(SCREEN_WIDTH / image_width)
    num_rows_per_pixel = int(SCREEN_HEIGHT / image_height)

    if (image_width * num_columns_per_pixel) != SCREEN_WIDTH:
        raise ValueError('Bad image_width: image_width {0} must be an exact integer divisor of {1}'.
                         format(image_width, SCREEN_WIDTH))

    if (image_height * num_rows_per_pixel) != SCREEN_HEIGHT:
        raise ValueError('Bad image_height: image_height {0} must be an exact integer divisor of {1}'.
                         format(image_height, SCREEN_HEIGHT))

    pixel_chunks = zip(*[iter(pixel_data)] * 8)  # convert into 8 pixel chunks - we'll pack each as 1 byte later
    pixel_chunks_per_row = int(SCREEN_WIDTH / 8)  # 8 pixels per byte (pixel-chunk)

    result_bytes = bytearray()

    x = 0
    y = 0
    for pixel_chunk in pixel_chunks:
        # convert the 8 pixels in the chunk into bits to write out
        # write each pixel bit num_columns_per_pixel times in a row
        pixel_byte = 0
        for pixel in pixel_chunk:
            for _ in range(num_columns_per_pixel):
                pixel_byte <<= 1
                pixel_byte += pixel
                x += 1
                if (x % 8) == 0:
                    result_bytes.append(pixel_byte)
                    pixel_byte = 0

        # check if this is the end of a row
        if x == SCREEN_WIDTH:
            x = 0
            y += 1

        if (x == 0) and (num_rows_per_pixel > 0):
            # at the end of a row - copy that row for every extra row-per-pixel
            for _ in range(num_rows_per_pixel-1):
                start_of_last_row = len(result_bytes) - pixel_chunks_per_row
                result_bytes.extend(result_bytes[start_of_last_row:])

    return result_bytes


def convert_image_to_screen_data(image, invert_image=False, pixel_threshold=127):
    ''' Convert an image into the correct format to display on Cozmo's face.

    Args:
        image (:class:`~PIL.Image.Image`): The image to display on Cozmo's face
        invert_image (bool): If true then pixels darker than the threshold are set on
        pixel_threshold (int): The grayscale threshold for what to consider on or off (0..255)

    Returns:
        A :class:`bytearray` object representing all of the pixels (8 pixels packed per byte)
    '''

    # convert to grayscale
    grayscale_image = image.convert('L')

    # convert to binary white/black (1/0)
    if invert_image:
        def pixel_func(x): return 1 if x <= pixel_threshold else 0
    else:
        def pixel_func(x): return 1 if x >= pixel_threshold else 0
    bw = grayscale_image.point(pixel_func, '1')

    # convert to a flattened 1D bytes object of pixel values (1s or 0s in this case)
    pixel_data = bytes(bw.getdata())

    return convert_pixels_to_screen_data(pixel_data, image.width, image.height)
