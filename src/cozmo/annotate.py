# Copyright (c) 2016-2017 Anki, Inc.
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

'''Camera image annotation.

.. image:: ../images/annotate.jpg

This module defines an :class:`ImageAnnotator` class used by
:class:`cozmo.world.World` to add annotations to camera images received by Cozmo.

This can include the location of cubes, faces and pets that Cozmo currently sees,
along with user-defined custom annotations.

The ImageAnnotator instance can be accessed as
:attr:`cozmo.world.World.image_annotator`.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['DEFAULT_OBJECT_COLORS',
           'TOP_LEFT', 'TOP_RIGHT', 'BOTTOM_LEFT', 'BOTTOM_RIGHT',
           'RESAMPLE_MODE_NEAREST', 'RESAMPLE_MODE_BILINEAR',
           'ImageText', 'Annotator', 'ObjectAnnotator', 'FaceAnnotator',
           'PetAnnotator', 'TextAnnotator', 'ImageAnnotator',
           'add_img_box_to_image', 'add_polygon_to_image', 'annotator']


import collections
import functools

try:
    from PIL import Image, ImageDraw
except (ImportError, SyntaxError):
    # may get SyntaxError if accidentally importing old Python 2 version of PIL
    ImageDraw = None

from . import event
from . import objects


DEFAULT_OBJECT_COLORS = {
    objects.LightCube: 'yellow',
    objects.CustomObject: 'purple',
    'default': 'red'
}

LEFT = 1
RIGHT = 2
TOP = 4
BOTTOM = 8

#: Top left position
TOP_LEFT = TOP | LEFT

#: Bottom left position
BOTTOM_LEFT = BOTTOM | LEFT

#: Top right position
TOP_RIGHT = TOP | RIGHT

#: Bottom right position
BOTTOM_RIGHT = BOTTOM | RIGHT

if ImageDraw is not None:
    #: Fastest resampling mode, use nearest pixel
    RESAMPLE_MODE_NEAREST = Image.NEAREST
    #: Slower, but smoother, resampling mode - linear interpolation from 2x2 grid of pixels
    RESAMPLE_MODE_BILINEAR = Image.BILINEAR
else:
    RESAMPLE_MODE_NEAREST = None
    RESAMPLE_MODE_BILINEAR = None


class ImageText:
    '''ImageText represents some text that can be applied to an image.

    The class allows the text to be placed at various positions inside a
    bounding box within the image itself.

    Args:
        text (string): The text to display; may contain newlines
        position (int): Where on the screen to render the text
            - A constant such at TOP_LEFT or BOTTOM_RIGHT
        align (string): Text alignment for multi-line strings
        color (string): Color to use for the text - see :mod:`PIL.ImageColor`
        font (:mod:`PIL.ImageFont`): Font to use (None for a default font)
        line_spacing (int): The vertical spacing for multi-line strings
        outline_color (string): Color to use for the outline - see
            :mod:`PIL.ImageColor` - use None for no outline.
        full_outline (bool): True if the outline should surround the text,
            otherwise a cheaper drop-shadow is displayed. Only relevant if
            outline_color is specified.
    '''
    def __init__(self, text, position=BOTTOM_RIGHT, align="left", color="white",
                 font=None, line_spacing=3, outline_color=None, full_outline=True):
        self.text = text
        self.position = position
        self.align = align
        self.color = color
        self.font = font
        self.line_spacing = line_spacing
        self.outline_color = outline_color
        self.full_outline = full_outline

    def render(self, draw, bounds):
        '''Renders the text onto an image within the specified bounding box.

        Args:
            draw (:class:`PIL.ImageDraw.ImageDraw`): The drawable surface to write on
            bounds (tuple of int)
                (top_left_x, top_left_y, bottom_right_x, bottom_right_y):
                bounding box
        Returns:
            The same :class:`PIL.ImageDraw.ImageDraw` object as was passed-in with text applied.
        '''
        (bx1, by1, bx2, by2) = bounds
        text_width, text_height = draw.textsize(self.text, font=self.font)

        if self.position & TOP:
            y = by1
        else:
            y = by2 - text_height

        if self.position & LEFT:
            x = bx1
        else:
            x = bx2 - text_width

        # helper method for each draw call below
        def _draw_text(pos, color):
            draw.text(pos, self.text, font=self.font, fill=color,
                      align=self.align, spacing=self.line_spacing)

        if self.outline_color is not None:
            # Pillow doesn't support outlined or shadowed text directly.
            # We manually draw the text multiple times to achieve the effect.
            if self.full_outline:
                _draw_text((x-1, y), self.outline_color)
                _draw_text((x+1, y), self.outline_color)
                _draw_text((x, y-1), self.outline_color)
                _draw_text((x, y+1), self.outline_color)
            else:
                # just draw a drop shadow (cheaper)
                _draw_text((x+1, y+1), self.outline_color)

        _draw_text((x,y), self.color)

        return draw


def add_img_box_to_image(image, box, color, text=None):
    '''Draw a box on an image and optionally add text.

    This will draw the outline of a rectangle to the passed in image
    in the specified color and optionally add one or more pieces of text
    along the inside edge of the rectangle.

    Args:
        image (:class:`PIL.Image.Image`): The image to draw on
        box (:class:`cozmo.util.ImageBox`): The ImageBox defining the rectangle to draw
        color (string): A color string suitable for use with PIL - see :mod:`PIL.ImageColor`
        text (instance or iterable of :class:`ImageText`): The text to display
            - may be a single ImageText instance, or any iterable (eg a list
            of ImageText instances) to display multiple pieces of text.
    '''
    d = ImageDraw.Draw(image)
    x1, y1 = box.left_x, box.top_y
    x2, y2 = box.right_x, box.bottom_y
    d.rectangle([x1, y1, x2, y2], outline=color)
    if text is not None:
        if isinstance(text, collections.Iterable):
            for t in text:
                t.render(d, (x1, y1, x2, y2))
        else:
            text.render(d, (x1, y1, x2, y2))


def add_polygon_to_image(image, poly_points, scale, line_color, fill_color=None):
    '''Draw a polygon on an image

    This will draw a polygon on the passed-in image in the specified
    colors and scale.

    Args:
        image (:class:`PIL.Image.Image`): The image to draw on
        poly_points: A sequence of points representing the polygon,
            where each point has float members (x, y)
        scale (float): Scale to multiply each point to match the image scaling
        line_color (string): The color for the outline of the polygon. The string value
            must be a color string suitable for use with PIL - see :mod:`PIL.ImageColor`
        fill_color (string): The color for the inside of the polygon. The string value
            must be a color string suitable for use with PIL - see :mod:`PIL.ImageColor`
    '''
    if len(poly_points) < 2:
        # Need at least 2 points to draw any lines
        return
    d = ImageDraw.Draw(image)

    # Convert poly_points to the PIL format and scale them to the image
    pil_poly_points = []
    for pt in poly_points:
        pil_poly_points.append((pt.x * scale, pt.y * scale))

    d.polygon(pil_poly_points, fill=fill_color, outline=line_color)


def _find_key_for_cls(d, cls):
    for cls in cls.__mro__:
        result = d.get(cls, None)
        if result:
            return result
    return d['default']


class Annotator:
    '''Annotation base class

    Subclasses of Annotator handle applying a single annotation to an image.
    '''
    #: int: The priority of the annotator - Annotators with higher numbered 
    #: priorities are applied first.
    priority = 100

    def __init__(self, img_annotator, priority=None):
        #: :class:`ImageAnnotator`: The object managing camera annotations
        self.img_annotator = img_annotator

        #: :class:`~cozmo.world.World`: The world object for the robot who owns the camera
        self.world = img_annotator.world

        #: bool: Set enabled to false to prevent the annotator being called
        self.enabled = True

        if priority is not None:
            self.priority = priority

    def apply(self, image, scale):
        '''Applies the annotation to the image.'''
        # should be overriden by a subclass
        raise NotImplementedError()

    def __hash__(self):
        return id(self)


class ObjectAnnotator(Annotator):
    '''Adds object annotations to an Image.

    This handles :class:`cozmo.objects.LightCube` objects
    as well as custom objects.
    '''
    priority = 100
    object_colors = DEFAULT_OBJECT_COLORS

    def __init__(self, img_annotator, object_colors=None):
        super().__init__(img_annotator)
        if object_colors is not None:
            self.object_colors = object_colors

    def apply(self, image, scale):
        d = ImageDraw.Draw(image)
        for obj in self.world.visible_objects:
            color = _find_key_for_cls(self.object_colors, obj.__class__)
            text = self.label_for_obj(obj)
            box = obj.last_observed_image_box
            if scale != 1:
                box *= scale
            add_img_box_to_image(image, box, color, text=text)

    def label_for_obj(self, obj):
        '''Fetch a label to display for the object.

        Override or replace to customize.
        '''
        return ImageText(obj.descriptive_name)


class FaceAnnotator(Annotator):
    '''Adds annotations of currently detected faces to a camera image.

    This handles the display of :class:`cozmo.faces.Face` objects.
    '''
    priority = 100
    box_color = 'green'

    def __init__(self, img_annotator, box_color=None):
        super().__init__(img_annotator)
        if box_color is not None:
            self.box_color = box_color

    def apply(self, image, scale):
        d = ImageDraw.Draw(image)
        for obj in self.world.visible_faces:
            text = self.label_for_face(obj)
            box = obj.last_observed_image_box
            if scale != 1:
                box *= scale
            add_img_box_to_image(image, box, self.box_color, text=text)
            add_polygon_to_image(image, obj.left_eye, scale, self.box_color)
            add_polygon_to_image(image, obj.right_eye, scale, self.box_color)
            add_polygon_to_image(image, obj.nose, scale, self.box_color)
            add_polygon_to_image(image, obj.mouth, scale, self.box_color)

    def label_for_face(self, obj):
        '''Fetch a label to display for the face.

        Override or replace to customize.
        '''
        expression = obj.known_expression
        if len(expression) > 0:
            # if there is a specific known expression, then also show the score
            # (display a % to make it clear the value is out of 100)
            expression += "=%s%% " % obj.expression_score
        if obj.name:
            return ImageText('%s%s (%d)' % (expression, obj.name, obj.face_id))
        return ImageText('(unknown%s face %d)' % (expression, obj.face_id))


class PetAnnotator(Annotator):
    '''Adds annotations of currently detected pets to a camera image.

    This handles the display of :class:`cozmo.pets.Pet` objects.
    '''
    priority = 100
    box_color = 'lightgreen'

    def __init__(self, img_annotator, box_color=None):
        super().__init__(img_annotator)
        if box_color is not None:
            self.box_color = box_color

    def apply(self, image, scale):
        d = ImageDraw.Draw(image)
        for obj in self.world.visible_pets:
            text = self.label_for_pet(obj)
            box = obj.last_observed_image_box
            if scale != 1:
                box *= scale
            add_img_box_to_image(image, box, self.box_color, text=text)

    def label_for_pet(self, obj):
        '''Fetch a label to display for the pet.

        Override or replace to customize.
        '''
        return ImageText('%d: %s' % (obj.pet_id, obj.pet_type))


class TextAnnotator(Annotator):
    '''Adds simple text annotations to a camera image.
    '''
    priority = 50

    def __init__(self, img_annotator, text):
        super().__init__(img_annotator)
        self.text = text

    def apply(self, image, scale):
        d = ImageDraw.Draw(image)
        self.text.render(d, (0, 0, image.width, image.height))


class _AnnotatorHelper(Annotator):
    def __init__(self, img_annotator, wrapped):
        super().__init__(img_annotator)
        self._wrapped = wrapped

    def apply(self, image, scale):
        self._wrapped(image, scale, world=self.world, img_annotator=self.img_annotator)


def annotator(f):
    '''A decorator for converting a regular function/method into an Annotator.

    The wrapped function should have a signature of
    ``(image, scale, img_annotator=None, world=None, **kw)``
    '''
    @functools.wraps(f)
    def wrapper(img_annotator):
        return _AnnotatorHelper(img_annotator, f)
    return wrapper


class ImageAnnotator(event.Dispatcher):
    '''ImageAnnotator applies annotations to the camera image received from the robot.

    This is instantiated by :class:`cozmo.world.World` and is accessible as
    :class:`cozmo.world.World.image_annotator`.

    By default it defines three active annotators named ``objects``, ``faces`` and ``pets``.

    The ``objects`` annotator adds a box around each object (such as light cubes)
    that Cozmo can see.  The ``faces`` annotator adds a box around each person's
    face that Cozmo can recognize. The ``pets`` annotator adds a box around each pet
    face that Cozmo can recognize.

    Custom annotations can be defined by calling :meth:`add_annotator` with
    a name of your choosing and an instance of a :class:`Annotator` subclass,
    or use a regular function wrapped with the :func:`annotator` decorator.

    Individual annotations can be disabled and re-enabled using the
    :meth:`disable_annotator` and :meth:`enable_annotator` methods.

    All annotations can be disabled by setting the
    :attr:`annotation_enabled` property to False.

    E.g. to disable face annotations, call
    ``coz.world.image_annotator.disable_annotator('faces')``

    Annotators each have a priority number associated with them. Annotators
    with a larger priority number are rendered first and may be overdrawn by those
    with a lower/smaller priority number.
    '''
    def __init__(self, world, **kw):
        super().__init__(**kw)
        #: :class:`cozmo.world.World`: World object that created the annotator.
        self.world = world

        self._annotators = {}
        self._sorted_annotators = []
        self.add_annotator('objects', ObjectAnnotator(self))
        self.add_annotator('faces', FaceAnnotator(self))
        self.add_annotator('pets', PetAnnotator(self))

        #: If this attribute is set to false, the :meth:`annotate_image` method
        #: will continue to provide a scaled image, but will not apply any annotations.
        self.annotation_enabled = True

    def _sort_annotators(self):
        self._sorted_annotators = sorted(self._annotators.values(),
                key=lambda an: an.priority, reverse=True)

    def add_annotator(self, name, annotator):
        '''Adds a new annotator for display.

        Annotators are enabled by default.

        Args:
            name (string): An arbitrary name for the annotator; must not
                already be defined
            annotator (:class:`Annotator` or callable): The annotator to add
                may either by an instance of Annotator, or a factory callable
                that will return an instance of Annotator. The callable will
                be called with an ImageAnnotator instance as its first argument.
        Raises:
            :class:`ValueError` if the annotator is already defined.
        '''
        if name in self._annotators:
            raise ValueError('Annotator "%s" is already defined' % (name))
        if not isinstance(annotator, Annotator):
            annotator = annotator(self)
        self._annotators[name] = annotator
        self._sort_annotators()

    def remove_annotator(self, name):
        '''Remove an annotator.

        Args:
            name (string): The name of the annotator to remove as passed to
                :meth:`add_annotator`.
        Raises:
            KeyError if the annotator isn't registered
        '''
        del self._annotators[name]
        self._sort_annotators()

    def get_annotator(self, name):
        '''Return a named annotator.

        Args:
            name (string): The name of the annotator to return
        Raises:
            KeyError if the annotator isn't registered
        '''
        return self._annotators[name]

    def disable_annotator(self, name):
        '''Disable a named annotator.

        Leaves the annotator as registered, but does not include its output
        in the annotated image.

        Args:
            name (string): The name of the annotator to disable
        '''
        if name in self._annotators:
            self._annotators[name].enabled = False

    def enable_annotator(self, name):
        '''Enabled a named annotator.

        (re)enable an annotator if it was previously disabled.

        Args:
            name (string): The name of the annotator to enable
        '''
        self._annotators[name].enabled = True

    def add_static_text(self, name, text, color='white', position=TOP_LEFT):
        '''Add some static text to annotated images.

        This is a convenience method to create a :class:`TextAnnnotator`
        and add it to the image.

        Args:
            name (string): An arbitrary name for the annotator; must not
                already be defined
            text (str or :class:`ImageText` instance): The text to display
                may be a plain string, or an ImageText instance
            color (string): Used if text is a string; defaults to white
            position (int): Used if text is a string; defaults to TOP_LEFT
        '''
        if isinstance(text, str):
            text = ImageText(text, position=position, color=color)
        self.add_annotator(name, TextAnnotator(self, text))

    def annotate_image(self, image, scale=None, fit_size=None, resample_mode=RESAMPLE_MODE_NEAREST):
        '''Called by :class:`~cozmo.world.World` to annotate camera images.

        Args:
            image (:class:`PIL.Image.Image`): The image to annotate
            scale (float): If set then the base image will be scaled by the
                supplied multiplier.  Cannot be combined with fit_size
            fit_size (tuple of int):  If set, then scale the image to fit inside
                the supplied (width, height) dimensions. The original aspect
                ratio will be preserved.  Cannot be combined with scale.
            resample_mode (int): The resampling mode to use when scaling the
                image. Should be either :attr:`RESAMPLE_MODE_NEAREST` (fast) or
                :attr:`RESAMPLE_MODE_BILINEAR` (slower, but smoother).
        Returns:
            :class:`PIL.Image.Image`
        '''
        if ImageDraw is None:
            return image

        if scale is not None:
            if scale == 1:
                image = image.copy()
            else:
                image = image.resize((int(image.width * scale), int(image.height * scale)),
                                     resample=resample_mode)

        elif fit_size is not None:
            if fit_size == (image.width, image.height):
                image = image.copy()
                scale = 1
            else:
                img_ratio = image.width / image.height
                fit_width, fit_height = fit_size
                fit_ratio = fit_width / fit_height
                if img_ratio > fit_ratio:
                    fit_height = int(fit_width / img_ratio)
                elif img_ratio < fit_ratio:
                    fit_width = int(fit_height * img_ratio)
                scale = fit_width / image.width
                image = image.resize((fit_width, fit_height))

        else:
            scale = 1

        if not self.annotation_enabled:
            return image

        for an in self._sorted_annotators:
            if an.enabled:
                an.apply(image, scale)

        return image
