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

'''This module provides a simple GUI viewer for Cozmo's camera.

It uses Tkinter, the standard Python GUI toolkit which is optionally available
on most platforms, and also depends on the Pillow and numpy libraries for
image processing.


See the online SDK documentation for details on how to install these extra
packages on your platform.

The easiest way to make use of this viewer is to call
:func:`cozmo.run.connect_with_tkviewer`.

Warning:
    This package requires Python to have Tkinter installed to display the GUI.
'''


# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['TkImageViewer']

import cozmo
import collections
import functools
import queue
import platform
import time

from PIL import Image, ImageDraw, ImageTk
import tkinter

from . import world


class TkThreadable:
    '''A mixin for adding threadsafe calls to tkinter methods.'''
    def __init__(self, *a, **kw):
        self._thread_queue = queue.Queue()
        self.after(50, self._thread_call_dispatch)

    def call_threadsafe(self, method, *a, **kw):
        self._thread_queue.put((method, a, kw))

    def _thread_call_dispatch(self):
        while True:
            try:
                method, a, kw = self._thread_queue.get(block=False)
                self.after_idle(method, *a, **kw)
            except queue.Empty:
                break
        self.after(50, self._thread_call_dispatch)


class TkImageViewer(tkinter.Frame, TkThreadable):
    '''Simple Tkinter camera viewer.'''

    # TODO: rewrite this whole thing.  Make a generic camera widget
    # that can be used in other Tk applications.  Also handle resizing
    # the window properly.
    def __init__(self,
            tk_root=None, refresh_interval=10, image_scale = 2,
            window_name = "CozmoView", force_on_top=True):
        if tk_root is None:
            tk_root = tkinter.Tk()
        tkinter.Frame.__init__(self, tk_root)
        TkThreadable.__init__(self)
        self._img_queue = collections.deque(maxlen=1)

        self._refresh_interval = refresh_interval
        self.scale = image_scale
        self.width = None
        self.height = None

        self.tk_root = tk_root
        tk_root.wm_title(window_name)

        self.label  = tkinter.Label(self.tk_root,image=None)
        self.tk_root.protocol("WM_DELETE_WINDOW", self._delete_window)
        self._isRunning = True
        self.robot = None
        self.handler = None
        self._first_image = True
        tk_root.aspect(4,3,4,3)

        if force_on_top:
            # force window on top of all others, regardless of focus
            tk_root.wm_attributes("-topmost", 1)

        self.last_configure = time.time()
        self.tk_root.bind("<Configure>", self.configure)
        self._repeat_draw_frame()

    async def connect(self, coz_conn):
        self.robot = await coz_conn.wait_for_robot()
        self.robot.camera.image_stream_enabled = True
        self.handler = self.robot.world.add_event_handler(
            world.EvtNewCameraImage, self.image_event)

    def disconnect(self):
        if self.handler:
            self.handler.disable()
        self.call_threadsafe(self.quit)

    def configure(self, event):
        # hack to interrupt feedback loop between image resizing
        # and frame resize detection; there has to be a better solution to this.
        if time.time() - self.last_configure < 0.1:
            return
        if event.width < 50 or event.height < 50:
            return
        self.last_configure = time.time()
        self.height = event.height
        self.width = event.width


    def image_event(self, evt, *, image, **kw):
        if self._first_image or self.width is None:
            img = image.annotate_image(scale=self.scale)
            self._first_image = False
        else:
            img = image.annotate_image(fit_size=(self.width, self.height))
        self._img_queue.append(img)

    def _delete_window(self):
        self.tk_root.destroy()
        self.quit()
        self._isRunning = False

    def _draw_frame(self):
        if ImageTk is None:
            return

        try:
            image = self._img_queue.popleft()
        except IndexError:
            # no new image
            return

        photoImage = ImageTk.PhotoImage(image)

        self.label.configure(image=photoImage)
        self.label.image = photoImage
        self.label.pack()

    def _repeat_draw_frame(self, event=None):
        self._draw_frame()
        self.after(self._refresh_interval, self._repeat_draw_frame)
