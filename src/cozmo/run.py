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

'''The run module contains helper classes and functions for opening a connection to the engine.

To get started, the :func:`connect` function can be used to open a connection
and run your own code connected to a :class:`cozmo.conn.CozmoConnection`
instance.  It takes care of setting up an event loop, finding the Android or
iOS device running the Cozmo app and making sure the connection is ok.

You can also use the :func:`connect_with_tkviewer` function which works in
a similar way to :func:`connect`, but will also display a window on the screen
showing a view from Cozmo's camera, if your system supports Tk.

Finally, more advanced progarms can integrate the SDK with an existing event
loop by using the :func:`connect_with_loop` function.

All of these functions make use of a :class:`DeviceConnector` subclass to
deal with actually connecting to an Android or iOS device.  There shouldn't
normally be a need to modify them or write your own.
'''

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['DeviceConnector', 'IOSConnector', 'AndroidConnector',
           'connect',  'connect_with_tkviewer', 'connect_on_loop',
           'setup_basic_logging']

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


class DeviceConnector:
    '''Base class for objects that setup the physical connection to a device.'''
    def __init__(self, cozmo_port=COZMO_PORT, enable_env_vars=True):
        self.cozmo_port = cozmo_port
        if enable_env_vars:
            self.parse_env_vars()

    async def connect(self, loop, protocol_factory):
        '''Connect attempts to open a connection transport to the Cozmo app on a device.

        On opening a transport it will create a protocol from the supplied
        factory and connect it to the transport, returning a (transport, protocol)
        tuple. See :meth:`asyncio.BaseEventLoop.create_connection`
        '''
        raise NotImplemented()

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
    '''
    def __init__(self, **kw):
        super().__init__(**kw)
        self.usbmux = None

    async def connect(self, loop, protocol_factory, conn_check):
        if not self.usbmux:
            self.usbmux = await usbmux.connect_to_usbmux(loop=loop)
        transport, proto = await self.usbmux.connect_to_first_device(protocol_factory, self.cozmo_port)
        if conn_check is not None:
            await conn_check(proto)
        logger.info('Connected to iOS device')
        return transport, proto


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
    '''
    def __init__(self, adb_cmd=None, **kw):
        self._adb_cmd = None
        super().__init__(**kw)

        self.portspec = 'tcp:' + str(self.cozmo_port)
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
        for serial in self._devices():
            logger.debug('Checking connection to Android device: %s', serial)
            try:
                self._remove_forward(serial)
            except:
                pass
            self._add_forward(serial)
            try:
                transport, proto = await loop.create_connection(protocol_factory, '127.0.0.1', self.cozmo_port)
                if conn_check:
                    # Check that we have a good connection before returning
                    try:
                        await conn_check(proto)
                    except Exception as e:
                        logger.debug('Failed connection check: %s', e)
                        raise

                logger.info('Connected to Android device: %s', serial)
                return transport, proto
            except:
                pass
            self._remove_forward(serial)
        raise ValueError("No connected Android devices running Cozmo in SDK mode")


class TCPConnector(DeviceConnector):
    '''Connects to the Cozmo app directly via TCP.

    Generally only used for testing and debugging.

    Requires that a SDK_TCP_PORT environment variable be set to the port
    number to connect to.
    '''
    def __init__(self, tcp_port=None, **kw):
        super().__init__(**kw)

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
        try:
            transport, proto = await loop.create_connection(protocol_factory, '127.0.0.1', self.tcp_port)
            if conn_check:
                try:
                    await conn_check(proto)
                except Exception as e:
                    logger.debug('Failed connection check: %s', e)
                    raise exceptions.ConnectionCheckFailed('Failed connection check: %s' % e)
            logger.info("Connected to device on TCP port %d" % self.tcp_port)
            return transport, proto
        except Exception as e:
            raise ValueError("No connected device running Cozmo in SDK mode on port %d" % self.tcp_port)


class FirstAvailableConnector(DeviceConnector):
    '''Connects to the first Android or iOS device running the Cozmo app in SDK mode.

    This class creates an :class:`AndroidConnector` or :class:`IOSConnector`
    instance and returns the first successful connection.

    This is the default connector used by ``connect_`` functions.
    '''
    def __init__(self):
        pass

    async def _do_connect(self, connector,loop, protocol_factory, conn_check):
        connect = connector.connect(loop, protocol_factory, conn_check)
        result = await asyncio.gather(connect, loop=loop, return_exceptions=True)
        return result[0]

    async def connect(self, loop, protocol_factory, conn_check):
        conn_args = (loop, protocol_factory, conn_check)

        tcp = TCPConnector()
        if tcp.enabled:
            result = await self._do_connect(tcp, *conn_args)
            if not isinstance(result, BaseException):
                return result
            logger.warn('No TCP connection found running Cozmo: %s' % result)

        android = AndroidConnector()
        result = await self._do_connect(android, *conn_args)
        if not isinstance(result, BaseException):
            return result
        logger.warn('No Android device found running Cozmo: %s' % result)

        ios = IOSConnector()
        result = await self._do_connect(ios, *conn_args)
        if not isinstance(result, BaseException):
            return result
        logger.warn('No iOS device found running Cozmo: %s' % result)

        raise exceptions.NoDevicesFound('No devices connected running Cozmo in SDK mode')



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
    finally:
        loop.run_until_complete(coz_conn.shutdown())
        loop.stop()
        loop.run_forever()


def _connect_sync(f, conn_factory=conn.CozmoConnection, connector=None):
    loop = asyncio.new_event_loop()
    abort_future = concurrent.futures.Future()
    conn_factory = functools.partial(conn_factory, _sync_abort_future=abort_future)
    lt = _LoopThread(loop, conn_factory=conn_factory, connector=connector, abort_future=abort_future)
    loop.set_exception_handler(functools.partial(_sync_exception_handler, abort_future))

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
        connector = FirstAvailableConnector()

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


def connect_with_tkviewer(f, conn_factory=conn.CozmoConnection, connector=None, force_on_top=False):
    '''Setup a connection to a device and run a user function while displaying Cozmo's camera.

    This display a Tk window on the screen showing a view of Cozmo's camera.
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


def setup_basic_logging(general_log_level=None, protocol_log_level=None,
        protocol_log_messages=clad_protocol.LOG_ALL, target=sys.stderr):
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
    '''
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
