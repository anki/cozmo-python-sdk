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

'''The run module contains helper classes and functions for opening a connection to the engine.

To get started, the :func:`run_program` function can be used for most cases,
it handles connecting to a device and then running the function you provide with
the SDK-provided Robot object passed in.

The :func:`connect` function can be used to open a connection
and run your own code connected to a :class:`cozmo.conn.CozmoConnection`
instance.  It takes care of setting up an event loop, finding the Android or
iOS device running the Cozmo app and making sure the connection is ok.

You can also use the :func:`connect_with_tkviewer` or :func:`connect_with_3dviewer`
functions which works in a similar way to :func:`connect`, but will also display
either a a window on the screen showing a view from Cozmo's camera (using Tk), or
a 3d viewer (with optional 2nd window showing Cozmo's camera) (using OpenGL), if
supported on your system.

Finally, more advanced progarms can integrate the SDK with an existing event
loop by using the :func:`connect_on_loop` function.

All of these functions make use of a :class:`DeviceConnector` subclass to
deal with actually connecting to an Android or iOS device.  There shouldn't
normally be a need to modify them or write your own.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['DeviceConnector', 'IOSConnector', 'AndroidConnector', 'TCPConnector',
           'connect', 'connect_with_3dviewer', 'connect_with_tkviewer', 'connect_on_loop',
           'run_program', 'setup_basic_logging']

import threading

import asyncio
import concurrent.futures
import functools
import inspect
import logging
import os
import os.path
import queue
import shutil
import subprocess
import sys
import types
import warnings

from . import logger, logger_protocol

from . import base
from . import clad_protocol
from . import conn
from . import event
from . import exceptions
from . import usbmux


#: The TCP port number we expect the Cozmo app to be listening on.
COZMO_PORT = 5106

if sys.platform in ('win32', 'cygwin'):
    DEFAULT_ADB_CMD = 'adb.exe'
else:
    DEFAULT_ADB_CMD = 'adb'


def _observe_connection_lost(proto, cb):
    meth = proto.connection_lost
    @functools.wraps(meth)
    def connection_lost(self, exc):
        meth(exc)
        cb()
    proto.connection_lost = types.MethodType(connection_lost, proto)


class DeviceConnector:
    '''Base class for objects that setup the physical connection to a device.'''
    def __init__(self, cozmo_port=COZMO_PORT, enable_env_vars=True):
        self.cozmo_port = cozmo_port
        if enable_env_vars:
            self.parse_env_vars()

    async def connect(self, loop, protocol_factory, conn_check):
        '''Connect attempts to open a connection transport to the Cozmo app on a device.

        On opening a transport it will create a protocol from the supplied
        factory and connect it to the transport, returning a (transport, protocol)
        tuple. See :meth:`asyncio.BaseEventLoop.create_connection`
        '''
        raise NotImplementedError

    def parse_env_vars(self):
        try:
            self.cozmo_port = int(os.environ['COZMO_PORT'])
        except (KeyError, ValueError):
            pass


class IOSConnector(DeviceConnector):
    '''Connects to an attached iOS device over USB.

    Opens a connection to the first iOS device that's found to be running
    the Cozmo app in SDK mode.

    iTunes (or another service providing usbmuxd) must be installed in order
    for this connector to be able to open a connection to a device.

    An instance of this class can be passed to the ``connect_`` prefixed
    functions in this module.

    Args:
        serial (string): Serial number of the device to connect to.
            If None, then connect to the first available iOS device running
            the Cozmo app in SDK mode.
    '''
    def __init__(self, serial=None, **kw):
        super().__init__(**kw)
        self.usbmux = None
        self._connected = set()
        self.serial = serial

    async def connect(self, loop, protocol_factory, conn_check):
        if not self.usbmux:
            self.usbmux = await usbmux.connect_to_usbmux(loop=loop)

        try:
            if self.serial is None:
                device_info, transport, proto = await self.usbmux.connect_to_first_device(
                        protocol_factory, self.cozmo_port, exclude=self._connected)

            else:
                device_id = await self.usbmux.wait_for_serial(self.serial)
                device_info, transport, proto = await self.usbmux.connect_to_device(
                        protocol_factory, device_id, self.cozmo_port)
        except asyncio.TimeoutError as exc:
            raise exceptions.ConnectionError("No connected iOS devices running Cozmo in SDK mode") from exc

        device_id = device_info.get('DeviceID')
        proto.device_info={
            'device_type': 'ios',
            'device_id': device_id,
            'serial':  device_info.get('SerialNumber')
        }

        if conn_check is not None:
            await conn_check(proto)

        self._connected.add(device_id)
        logger.info('Connected to iOS device_id=%s serial=%s', device_id,
                device_info.get('SerialNumber'))
        _observe_connection_lost(proto, functools.partial(self._disconnect, device_id))
        return transport, proto

    def _disconnect(self, device_id):
        logger.info('iOS device_id=%s disconnected.', device_id)
        self._connected.discard(device_id)


class AndroidConnector(DeviceConnector):
    '''Connects to an attached Android device over USB.

    This requires the Android Studio command line tools to be installed,
    specifically `adb`.

    By default the connector will attempt to locate `adb` (or `adb.exe`
    on Windows) in common locations, but it may also be supplied by setting
    the ``ANDROID_ADB_PATH`` environment variable, or by passing it
    to the constructor.

    An instance of this class can be passed to the ``connect_`` prefixed
    functions in this module.

    Args:
        serial (string): Serial number of the device to connect to.
            If None, then connect to the first available Android device running
            the Cozmo app in SDK mode.
    '''
    def __init__(self, adb_cmd=None, serial=None, **kw):
        self._adb_cmd = None
        super().__init__(**kw)

        self.serial = serial
        self.portspec = 'tcp:' + str(self.cozmo_port)
        self._connected = set()
        if adb_cmd:
            self._adb_cmd = adb_cmd
        else:
            self._adb_cmd = shutil.which(DEFAULT_ADB_CMD)

    def parse_env_vars(self):
        super().parse_env_vars()

        self._adb_cmd = os.environ.get('ANDROID_ADB_PATH')

    @property
    def adb_cmd(self):
        if self._adb_cmd is not None:
            return self._adb_cmd

        if sys.platform != 'win32':
            return DEFAULT_ADB_CMD

        # C:\Users\IEUser\AppData\Local\Android\android-sdk
        # C:\Program Files (x86)\Android\android-sdk
        try_paths = []
        for path in [os.environ[key] for key in ('LOCALAPPDATA', 'ProgramFiles', 'ProgramFiles(x86)') if key in os.environ]:
            try_paths.append(os.path.join(path, 'Android', 'android-sdk'))

        for path in try_paths:
            adb_path = os.path.join(path, 'platform-tools', 'adb.exe')
            if os.path.exists(adb_path):
                self._adb_cmd = adb_path
                logger.debug('Found adb.exe at %s', adb_path)
                return adb_path

        raise ValueError('Could not find Android development tools')

    def _exec(self, *args):
        try:
            result = subprocess.run([self.adb_cmd] + list(args),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        except Exception as e:
            raise ValueError('Failed to execute adb command %s: %s' % (self.adb_cmd, e))
        if result.returncode != 0:
            raise ValueError('Failed to execute adb command %s: %s' % (result.args, result.stderr))
        return result.stdout.split(b'\n')

    def _devices(self):
        for line in self._exec('devices'):
            line = line.split()
            if len(line) != 2 or line[1] != b'device':
                continue
            yield line[0].decode('ascii') # device serial #

    def _add_forward(self, serial):
        self._exec('-s', serial, 'forward', self.portspec, self.portspec)

    def _remove_forward(self, serial):
        self._exec('-s', serial, 'forward', '--remove', self.portspec)

    async def connect(self, loop, protocol_factory, conn_check):
        version_mismatch = None
        for serial in self._devices():
            if serial in self._connected:
                continue
            if self.serial is not None and serial.lower() != self.serial.lower():
                continue

            logger.debug('Checking connection to Android device: %s', serial)
            try:
                self._remove_forward(serial)
            except:
                pass
            self._add_forward(serial)
            try:
                transport, proto = await loop.create_connection(
                        protocol_factory, '127.0.0.1', self.cozmo_port)
                proto.device_info={
                    'device_type': 'android',
                    'serial':  serial,
                }
                if conn_check:
                    # Check that we have a good connection before returning
                    try:
                        await conn_check(proto)
                    except Exception as e:
                        logger.debug('Failed connection check: %s', e)
                        raise

                logger.info('Connected to Android device serial=%s', serial)
                self._connected.add(serial)
                _observe_connection_lost(proto, functools.partial(self._disconnect, serial))
                return transport, proto
            except exceptions.SDKVersionMismatch as e:
                version_mismatch = e
            except:
                pass
            self._remove_forward(serial)

        if version_mismatch is not None:
            raise version_mismatch

        raise exceptions.ConnectionError("No connected Android devices running Cozmo in SDK mode")

    def _disconnect(self, serial):
        logger.info('Android serial=%s disconnected.', serial)
        self._connected.discard(serial)


class TCPConnector(DeviceConnector):
    '''Connects to the Cozmo app directly via TCP.

    Generally only used for testing and debugging.

    Requires that a SDK_TCP_PORT environment variable be set to the port
    number to connect to.
    '''
    def __init__(self, tcp_port=None, ip_addr='127.0.0.1', **kw):
        super().__init__(**kw)

        self.ip_addr = ip_addr
        if tcp_port is not None:
            # override SDK_TCP_PORT environment variable
            self.tcp_port = tcp_port

    def parse_env_vars(self):
        super().parse_env_vars()

        self.tcp_port = None
        try:
            self.tcp_port = int(os.environ['SDK_TCP_PORT'])
        except (KeyError, ValueError):
            pass

    @property
    def enabled(self):
        return self.tcp_port is not None

    async def connect(self, loop, protocol_factory, conn_check):
        transport, proto = await loop.create_connection(protocol_factory, self.ip_addr, self.tcp_port)
        proto.device_info={
            'device_type': 'tcp',
            'host': '%s:%s' % (self.ip_addr, self.tcp_port),
        }
        if conn_check:
            try:
                await conn_check(proto)
            except Exception as e:
                logger.debug('Failed connection check: %s', e)
                raise
        logger.info("Connected to device on TCP port %d" % self.tcp_port)
        return transport, proto


class FirstAvailableConnector(DeviceConnector):
    '''Connects to the first Android or iOS device running the Cozmo app in SDK mode.

    This class creates an :class:`AndroidConnector` or :class:`IOSConnector`
    instance and returns the first successful connection.

    This is the default connector used by ``connect_`` functions.
    '''
    def __init__(self):
        super().__init__(self, enable_env_vars=False)
        self.tcp = TCPConnector()
        self.ios = IOSConnector()
        self.android = AndroidConnector()

    async def _do_connect(self, connector,loop, protocol_factory, conn_check):
        connect = connector.connect(loop, protocol_factory, conn_check)
        result = await asyncio.gather(connect, loop=loop, return_exceptions=True)
        return result[0]

    async def connect(self, loop, protocol_factory, conn_check):
        conn_args = (loop, protocol_factory, conn_check)

        tcp_result = None
        if self.tcp.enabled:
            tcp_result = await self._do_connect(self.tcp, *conn_args)
            if not isinstance(tcp_result, BaseException):
                return tcp_result
            logger.warning('No TCP connection found running Cozmo: %s', tcp_result)

        android_result = await self._do_connect(self.android, *conn_args)
        if not isinstance(android_result, BaseException):
            return android_result

        ios_result = await self._do_connect(self.ios, *conn_args)
        if not isinstance(ios_result, BaseException):
            return ios_result

        logger.warning('No iOS device found running Cozmo: %s', ios_result)
        logger.warning('No Android device found running Cozmo: %s', android_result)

        if isinstance(tcp_result, exceptions.SDKVersionMismatch):
            raise tcp_result
        if isinstance(ios_result, exceptions.SDKVersionMismatch):
            raise ios_result
        if isinstance(android_result, exceptions.SDKVersionMismatch):
            raise android_result

        raise exceptions.NoDevicesFound('No devices connected running Cozmo in SDK mode')


# Create an instance of a connector to use by default
# The instance will maintain state about which devices are currently connected.
_DEFAULT_CONNECTOR = FirstAvailableConnector()


def _sync_exception_handler(abort_future, loop, context):
    loop.default_exception_handler(context)
    exception = context.get('exception')
    if exception is not None:
        abort_future.set_exception(context['exception'])
    else:
        abort_future.set_exception(RuntimeError(context['message']))


class _LoopThread:
    '''Takes care of managing an event loop running in a dedicated thread.

    Args:
        loop (:class:`asyncio.BaseEventLoop`): The loop to run
        f (callable): Optional code to execute on the loop's thread
        conn_factory (callable): Override the factory function to generate a
            :class:`cozmo.conn.CozmoConnection` (or subclass) instance.
        connector (:class:`DeviceConnector`): Optional instance of a DeviceConnector
            subclass that handles opening the USB connection to a device.
            By default, it will connect to the first Android or iOS device that
            has the Cozmo app running in SDK mode.
        abort_future (:class:`concurrent.futures.Future): Optional future to
            raise an exception on in the event of an exception occurring within
            the thread.
    '''
    def __init__(self, loop, f=None, conn_factory=conn.CozmoConnection, connector=None, abort_future=None):
        self.loop = loop
        self.f = f
        if not abort_future:
            abort_future = concurrent.futures.Future()
        self.abort_future = abort_future
        self.conn_factory = conn_factory
        self.connector = connector
        self.thread = None
        self._running = False

    def start(self):
        '''Start a thread and open a connection to a device.

        Returns:
            :class:`cozmo.conn.CozmoConnection` instance
        '''
        q = queue.Queue()
        abort_future = concurrent.futures.Future()
        def run_loop():
            asyncio.set_event_loop(self.loop)
            try:
                coz_conn = connect_on_loop(self.loop, self.conn_factory, self.connector)
                q.put(coz_conn)
            except Exception as e:
                self.abort_future.set_exception(e)
                q.put(e)
                return

            if self.f:
                asyncio.ensure_future(self.f(coz_conn))
            self.loop.run_forever()

        self.thread = threading.Thread(target=run_loop)
        self.thread.start()

        coz_conn = q.get(10)
        if coz_conn is None:
            raise TimeoutError("Timed out waiting for connection to device")
        if isinstance(coz_conn, Exception):
            raise coz_conn
        self.coz_conn = coz_conn
        self._running = True
        return coz_conn


    def stop(self):
        '''Cleaning shutdown the running loop and thread.'''
        if self._running:
            async def _stop():
                await self.coz_conn.shutdown()
                self.loop.call_soon(lambda: self.loop.stop())
            asyncio.run_coroutine_threadsafe(_stop(), self.loop).result()
            self.thread.join()
            self._running = False

    def abort(self, exc):
        '''Abort the running loop and thread.'''
        if self._running:
            async def _abort(exc):
                self.coz_conn.abort(exc)
            asyncio.run_coroutine_threadsafe(_abort(exc), self.loop).result()
            self.stop()


def _connect_async(f, conn_factory=conn.CozmoConnection, connector=None):
    # use the default loop, if one is available for the current thread,
    # if not create  a new loop and make it the default.
    #
    # the expectation is that if the user wants explicit control over which
    # loop the code is executed on, they'll just use connect_on_loop directly.
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except:
        pass

    if loop is None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    coz_conn = connect_on_loop(loop, conn_factory, connector)
    try:
        loop.run_until_complete(f(coz_conn))
    except KeyboardInterrupt:
        logger.info('Exit requested by user')
    finally:
        loop.run_until_complete(coz_conn.shutdown())
        loop.stop()
        loop.run_forever()


_sync_loop = asyncio.new_event_loop()
def _connect_sync(f, conn_factory=conn.CozmoConnection, connector=None):
    abort_future = concurrent.futures.Future()
    conn_factory = functools.partial(conn_factory, _sync_abort_future=abort_future)
    lt = _LoopThread(_sync_loop, conn_factory=conn_factory, connector=connector, abort_future=abort_future)
    _sync_loop.set_exception_handler(functools.partial(_sync_exception_handler, abort_future))

    coz_conn = lt.start()

    try:
        f(base._SyncProxy(coz_conn))
    finally:
        lt.stop()


def connect_on_loop(loop, conn_factory=conn.CozmoConnection, connector=None):
    '''Uses the supplied event loop to connect to a device.

    Will run the event loop in the current thread until the
    connection succeeds or fails.

    If you do not want/need to manage your own loop, then use the
    :func:`connect` function to handle setup/teardown and execute
    a user-supplied function.

    Args:
        loop (:class:`asyncio.BaseEventLoop`): The event loop to use to
            connect to Cozmo.
        conn_factory (callable): Override the factory function to generate a
            :class:`cozmo.conn.CozmoConnection` (or subclass) instance.
        connector (:class:`DeviceConnector`): Optional instance of a DeviceConnector
            subclass that handles opening the USB connection to a device.
            By default, it will connect to the first Android or iOS device that
            has the Cozmo app running in SDK mode.

    Returns:
        A :class:`cozmo.conn.CozmoConnection` instance.
    '''
    if connector is None:
        connector = _DEFAULT_CONNECTOR

    factory = functools.partial(conn_factory, loop=loop)

    async def conn_check(coz_conn):
        await coz_conn.wait_for(conn.EvtConnected, timeout=5)

    async def connect():
        return await connector.connect(loop, factory, conn_check)

    transport, coz_conn = loop.run_until_complete(connect())
    return coz_conn


def connect(f, conn_factory=conn.CozmoConnection, connector=None):
    '''Connects to the Cozmo Engine on the mobile device and supplies the connection to a function.

    Accepts a function, f, that is given a :class:`cozmo.conn.CozmoConnection` object as
    a parameter.

    The supplied function may be either an asynchronous coroutine function
    (normally defined using ``async def``) or a regular synchronous function.

    If an asynchronous function is supplied it will be run on the same thread
    as the Cozmo event loop and must use the ``await`` keyword to yield control
    back to the loop.

    If a synchronous function is supplied then it will run on the main thread
    and Cozmo's event loop will run on a separate thread.  Calls to
    asynchronous methods returned from CozmoConnection will automatically
    be translated to synchronous ones.

    The connect function will return once the supplied function has completed,
    as which time it will terminate the connection to the robot.

    Args:
        f (callable): The function to execute
        conn_factory (callable): Override the factory function to generate a
            :class:`cozmo.conn.CozmoConnection` (or subclass) instance.
        connector (:class:`DeviceConnector`): Optional instance of a DeviceConnector
            subclass that handles opening the USB connection to a device.
            By default it will connect to the first Android or iOS device that
            has the Cozmo app running in SDK mode.
    '''
    if asyncio.iscoroutinefunction(f):
        return _connect_async(f, conn_factory, connector)
    return _connect_sync(f, conn_factory, connector)


def _connect_viewer(f, conn_factory, connector, viewer):
    # Run the viewer in the main thread, with the SDK running on a new background thread.
    loop = asyncio.new_event_loop()
    abort_future = concurrent.futures.Future()

    async def view_connector(coz_conn):
        try:
            await viewer.connect(coz_conn)

            if inspect.iscoroutinefunction(f):
                await f(coz_conn)
            else:
                await coz_conn._loop.run_in_executor(None, f, base._SyncProxy(coz_conn))
        finally:
            viewer.disconnect()

    try:
        if not inspect.iscoroutinefunction(f):
            conn_factory = functools.partial(conn_factory, _sync_abort_future=abort_future)
        lt = _LoopThread(loop, f=view_connector, conn_factory=conn_factory, connector=connector)
        lt.start()
        viewer.mainloop()
    except BaseException as e:
        abort_future.set_exception(exceptions.SDKShutdown(repr(e)))
        raise
    finally:
        lt.stop()


def connect_with_3dviewer(f, conn_factory=conn.CozmoConnection, connector=None,
                          enable_camera_view=False, show_viewer_controls=True):
    '''Setup a connection to a device and run a user function while displaying Cozmo's 3d world.

    This displays an OpenGL window on the screen with a 3D view of Cozmo's
    understanding of the world. Optionally, if `use_viewer` is True, a 2nd OpenGL
    window will also display showing a view of Cozmo's camera. It will return an
    error if the current system does not support PyOpenGL.

    The function may be either synchronous or asynchronous (defined
    used ``async def``).

    The function must accept a :class:`cozmo.CozmoConnection` object as
    its only argument.
    This call will block until the supplied function completes.

    Args:
        f (callable): The function to execute
        conn_factory (callable): Override the factory function to generate a
            :class:`cozmo.conn.CozmoConnection` (or subclass) instance.
        connector (:class:`DeviceConnector`): Optional instance of a DeviceConnector
            subclass that handles opening the USB connection to a device.
            By default it will connect to the first Android or iOS device that
            has the Cozmo app running in SDK mode.
        enable_camera_view (bool): Specifies whether to also open a 2D camera
            view in a second OpenGL window.
        show_viewer_controls (bool): Specifies whether to draw controls on the view.
    '''
    try:
        from . import opengl
    except ImportError as exc:
        opengl = exc

    if isinstance(opengl, Exception):
        if isinstance(opengl, exceptions.InvalidOpenGLGlutImplementation):
            raise NotImplementedError('GLUT (OpenGL Utility Toolkit) is not available:\n%s'
                                      % opengl)
        else:
            raise NotImplementedError('opengl is not available; '
                'make sure the PyOpenGL, PyOpenGL-accelerate and Pillow packages are installed:\n'
                'Do `pip3 install --user cozmo[3dviewer]` to install. Error: %s' % opengl)

    viewer = opengl.OpenGLViewer(enable_camera_view=enable_camera_view, show_viewer_controls=show_viewer_controls)

    _connect_viewer(f, conn_factory, connector, viewer)


def connect_with_tkviewer(f, conn_factory=conn.CozmoConnection, connector=None, force_on_top=False):
    '''Setup a connection to a device and run a user function while displaying Cozmo's camera.

    This displays a Tk window on the screen showing a view of Cozmo's camera.
    It will return an error if the current system does not support Tk.

    The function may be either synchronous or asynchronous (defined
    used ``async def``).

    The function must accept a :class:`cozmo.CozmoConnection` object as
    its only argument.
    This call will block until the supplied function completes.

    Args:
        f (callable): The function to execute
        conn_factory (callable): Override the factory function to generate a
            :class:`cozmo.conn.CozmoConnection` (or subclass) instance.
        connector (:class:`DeviceConnector`): Optional instance of a DeviceConnector
            subclass that handles opening the USB connection to a device.
            By default it will connect to the first Android or iOS device that
            has the Cozmo app running in SDK mode.
        force_on_top (bool): Specifies whether the window should be forced on top of all others
    '''
    try:
        from . import tkview
    except ImportError as exc:
        tkview = exc

    if isinstance(tkview, Exception):
        raise NotImplementedError('tkviewer not available on this platform; '
            'make sure Tkinter, NumPy and Pillow packages are installed (%s)' % tkview)

    viewer = tkview.TkImageViewer(force_on_top=force_on_top)

    _connect_viewer(f, conn_factory, connector, viewer)


def setup_basic_logging(general_log_level=None, protocol_log_level=None,
        protocol_log_messages=clad_protocol.LOG_ALL, target=sys.stderr,
        deprecated_filter="default"):
    '''Helper to perform basic setup of the Python logging machinery.

    The SDK defines two loggers:

    * :data:`logger` ("cozmo.general") - For general purpose information
      about events within the SDK; and
    * :data:`logger_protocol` ("cozmo.protocol") - For low level
      communication messages between the device and the SDK.

    Generally only :data:`logger` is interesting.

    Args:
        general_log_level (str): 'DEBUG', 'INFO', 'WARN', 'ERROR' or an equivalent
            constant from the :mod:`logging` module.  If None then a
            value will be read from the COZMO_LOG_LEVEL environment variable.
        protocol_log_level (str): as general_log_level.  If None then a
            value will be read from the COZMO_PROTOCOL_LOG_LEVEL environment
            variable.
        protocol_log_messages (list): The low level messages that should be
            logged to the protocol log.  Defaults to all.  Will read from
            the COMZO_PROTOCOL_LOG_MESSAGES if available which should be
            a comma separated list of message names (case sensitive).
        target (object): The stream to send the log data to; defaults to stderr
        deprecated_filter (str): The filter for any DeprecationWarning messages.
            This is defaulted to "default" which shows the warning once per
            location. You can hide all deprecated warnings by passing in "ignore",
            see https://docs.python.org/3/library/warnings.html#warning-filter
            for more information.
    '''
    if deprecated_filter is not None:
        warnings.filterwarnings(deprecated_filter, category=DeprecationWarning)

    if general_log_level is None:
        general_log_level = os.environ.get('COZMO_LOG_LEVEL', logging.INFO)
    if protocol_log_level is None:
        protocol_log_level = os.environ.get('COZMO_PROTOCOL_LOG_LEVEL', logging.INFO)
    if protocol_log_level:
        if 'COMZO_PROTOCOL_LOG_MESSAGES' in os.environ:
            lm = os.environ['COMZO_PROTOCOL_LOG_MESSAGES']
            if lm.lower() == 'all':
                clad_protocol.CLADProtocol._clad_log_which = clad_protocol.LOG_ALL
            else:
                clad_protocol.CLADProtocol._clad_log_which = set(lm.split(','))
        else:
            clad_protocol.CLADProtocol._clad_log_which = protocol_log_messages

    h = logging.StreamHandler(stream=target)
    f = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    h.setFormatter(f)
    logger.addHandler(h)
    logger. setLevel(general_log_level)
    if protocol_log_level is not None:
        logger_protocol.addHandler(h)
        logger_protocol.setLevel(protocol_log_level)


def run_program(f, use_viewer=False, conn_factory=conn.CozmoConnection,
                connector=None, force_viewer_on_top=False,
                deprecated_filter="default", use_3d_viewer=False,
                show_viewer_controls=True,
                exit_on_connection_error=True):
    '''Connect to Cozmo and run the provided program/function f.

    Args:

        f (callable): The function to execute, accepts a connected
            :class:`cozmo.robot.Robot` as the parameter.
        use_viewer (bool): Specifies whether to display a view of Cozmo's camera
            in a window.
        conn_factory (callable): Override the factory function to generate a
            :class:`cozmo.conn.CozmoConnection` (or subclass) instance.
        connector (:class:`DeviceConnector`): Optional instance of a DeviceConnector
            subclass that handles opening the USB connection to a device.
            By default it will connect to the first Android or iOS device that
            has the Cozmo app running in SDK mode.
        force_viewer_on_top (bool): Specifies whether the window should be
            forced on top of all others (only relevant if use_viewer is True).
            Note that this is ignored if use_3d_viewer is True (as it's not
            currently supported on that windowing system).
        deprecated_filter (str): The filter for any DeprecationWarning messages.
            This is defaulted to "default" which shows the warning once per
            location. You can hide all deprecated warnings by passing in "ignore",
            see https://docs.python.org/3/library/warnings.html#warning-filter
            for more information.
        use_3d_viewer (bool): Specifies whether to display a 3D view of Cozmo's
            understanding of the world in a window. Note that if both this and
            `use_viewer` are set then the 2D camera view will render in an OpenGL
            window instead of a TkView window.
        show_viewer_controls (bool): Specifies whether to draw controls on the view.
        exit_on_connection_error (bool): Specify whether the program should exit on
            connection error or should an error be raised. Default to true.
    '''
    setup_basic_logging(deprecated_filter=deprecated_filter)

    # Wrap f (a function that takes in an already created robot)
    # with a function that accepts a cozmo.conn.CozmoConnection
    if asyncio.iscoroutinefunction(f):
        @functools.wraps(f)
        async def wrapper(sdk_conn):
            try:
                robot = await sdk_conn.wait_for_robot()
                await f(robot)
            except exceptions.SDKShutdown:
                pass
            except KeyboardInterrupt:
                logger.info('Exit requested by user')
    else:
        @functools.wraps(f)
        def wrapper(sdk_conn):
            try:
                robot = sdk_conn.wait_for_robot()
                f(robot)
            except exceptions.SDKShutdown:
                pass
            except KeyboardInterrupt:
                logger.info('Exit requested by user')

    try:
        if use_3d_viewer:
            connect_with_3dviewer(wrapper, conn_factory=conn_factory, connector=connector,
                                  enable_camera_view=use_viewer, show_viewer_controls=show_viewer_controls)
        elif use_viewer:
            connect_with_tkviewer(wrapper, conn_factory=conn_factory, connector=connector,
                                  force_on_top=force_viewer_on_top)
        else:
            connect(wrapper, conn_factory=conn_factory, connector=connector)
    except KeyboardInterrupt:
        logger.info('Exit requested by user')
    except exceptions.ConnectionError as e:
        if exit_on_connection_error:
            sys.exit("A connection error occurred: %s" % e)
        else:
            logger.error("A connection error occurred: %s" % e)
            raise
