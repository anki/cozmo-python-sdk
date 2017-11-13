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

'''Wrappers and helpers for using Flask with Cozmo.

Flask is a Python web framework. remote_control_cozmo.py and other scripts may use
these utility functions to interact with a web browser.
'''

import logging
import sys
from threading import Thread
import webbrowser
from time import sleep
from io import BytesIO
try:
    from flask import make_response, Response, send_file
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install --user flask` to install")



def _delayed_open_web_browser(url, delay, new=0, autoraise=True, specific_browser=None):
    '''
    Spawn a thread and call sleep_and_open_web_browser from within it so that main thread can keep executing at the
    same time. Insert a small sleep before opening a web-browser
    this gives Flask a chance to start running before the browser starts requesting data from Flask.
    '''

    def _sleep_and_open_web_browser(url, delay, new, autoraise, specific_browser):
        sleep(delay)
        browser = webbrowser

        # E.g. On OSX the following would use the Chrome browser app from that location
        # specific_browser = 'open -a /Applications/Google\ Chrome.app %s'
        if specific_browser:
            browser = webbrowser.get(specific_browser)

        browser.open(url, new=new, autoraise=autoraise)

    thread = Thread(target=_sleep_and_open_web_browser,
                    kwargs=dict(url=url, new=new, autoraise=autoraise, delay=delay, specific_browser=specific_browser))
    thread.daemon = True # Force to quit on main quitting
    thread.start()


def run_flask(flask_app, host_ip="127.0.0.1", host_port=5000, enable_flask_logging=False,
              open_page=True, open_page_delay=1.0):
    '''
    Run the Flask webserver on specified host and port
    optionally also open that same host:port page in your browser to connect
    '''

    if not enable_flask_logging:
        # disable logging in Flask (it's enabled by default)
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    if open_page:
        # we add a delay (dispatched in another thread) to open the page so that the flask webserver is open
        # before the webpage requests any data
        _delayed_open_web_browser("http://" + host_ip + ":" + str(host_port), delay=open_page_delay)

    flask_app.run(host=host_ip, port=host_port, use_evalex=False, threaded=True)


def shutdown_flask(request):
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        sys.exit('SDK Shutdown')
    func()


def stream_video(streaming_function, url_root):
    return Response(streaming_function(url_root), mimetype='multipart/x-mixed-replace; boundary=frame')


def make_uncached_response(in_file):
    response = make_response(in_file)
    response.headers['Pragma-Directive'] = 'no-cache'
    response.headers['Cache-Directive'] = 'no-cache'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def serve_pil_image(pil_img, serve_as_jpeg=False, jpeg_quality=70):
    '''Convert PIL image to relevant image file and send it'''
    img_io = BytesIO()

    if serve_as_jpeg:
        pil_img.save(img_io, 'JPEG', quality=jpeg_quality)
        img_io.seek(0)
        return make_uncached_response(send_file(img_io, mimetype='image/jpeg',
                                                add_etags=False))
    else:
        pil_img.save(img_io, 'PNG')
        img_io.seek(0)
        return make_uncached_response(send_file(img_io, mimetype='image/png',
                                                add_etags=False))
