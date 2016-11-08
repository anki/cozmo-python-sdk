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

__all__ = ('USBMuxError', 'ProtocolError', 'DeviceNotConnected',
    'ConnectionRefused', 'ConnectionFailed', 'QueueNotifyCM', 'USBMux',
    'connect_to_usbmux')

import asyncio
import collections
import contextlib
import plistlib
import socket
import struct
import sys
import time


DEFAULT_SOCKET_PATH = '/var/run/usbmuxd'
DEFAULT_SOCKET_PORT = 27015
DEFAULT_MAX_WAIT = 2

PLIST_VERSION = 1

ACTION_ATTACHED = 'attached'
ACTION_DETACHED = 'detached'


class USBMuxError(Exception): pass

class ProtocolError(USBMuxError): pass

class DeviceNotConnected(USBMuxError): pass

class ConnectionRefused(USBMuxError): pass

class ConnectionFailed(USBMuxError): pass


class PlistProto(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self._buf = bytearray()

    def data_received(self, data):
        self._buf += data
        while len(self._buf) > 4:
            length = struct.unpack('I', self._buf[:4])[0]
            if len(self._buf) < length:
                return
            ver, req, tag = struct.unpack('III', self._buf[4:16])
            if ver != PLIST_VERSION:
                raise ProtocolError("Unsupported protocol version from usbmux stream")
            pldata = plistlib.loads(self._buf[16:length])
            self.msg_received(pldata)
            self._buf = self._buf[length:]

    def send_msg(self, **kw):
        pl = plistlib.dumps(kw)
        self.transport.write(struct.pack('IIII', len(pl) + 16, 1, 8, 1))
        self.transport.write(pl)

    def msg_received(self, msg):
        '''Called when a plist record is received'''


class USBMuxConnector(PlistProto):
    '''Opens a connection to a port on a device'''

    def __init__(self, device_id, port, waiter):
        self.device_id = device_id
        self.port = port
        self.waiter = waiter

    def connection_made(self, transport):
        super().connection_made(transport)

        self.send_msg(
                MessageType='Connect',
                ClientVersionString='pyusbmux',
                ProgName='pyusbmux',
                DeviceID=self.device_id,
                PortNumber=socket.htons(self.port)
            )

    def connection_lost(self, exc):
        if self.waiter.done():
            return
        self.waiter.set_exception(exc)

    def msg_received(self, msg):
        if msg['MessageType'] != 'Result':
            return
        status = msg['Number']
        if status == 0:
            self.waiter.set_result(None)

            # ensure no futher data is received until the protocol
            # is switched to the application protocol.
            self.transport.pause_reading()

        elif status == 2:
            self.waiter.set_exception(DeviceNotConnected("Device %s is not currently connected" % (self.device_id,)))

        elif status == 3:
            self.waiter.set_exception(ConnectionRefused("Connection refused to device_id=%s port=%d" % (self.device_id, self.port)))

        else:
            self.waiter.set_exception(ConnectionFailed("Protocol error connecting to device %s" % (self.device_id,)))


class _ProtoSwitcher(asyncio.Protocol):
    def __init__(self, loop, initial_protocol):
        self._loop = loop
        self._transport = None
        self.protocol = initial_protocol

    def switch_protocol(self, protocol_factory):
        self.protocol = protocol_factory()
        if self._transport:
            self._loop.call_soon(self.protocol.connection_made, self._transport)
            self._loop.call_soon(self._transport.resume_reading)
        return self.protocol

    def connection_made(self, transport):
        self._transport = transport
        self.protocol.connection_made(transport)

    def connection_lost(self, exc):
        self.protocol.connection_lost(exc)

    def pause_writing(self):
        self.protocol.pause_writing()

    def resume_writing(self):
        self.protocol.resume_writing()

    def data_received(self, data):
        self.protocol.data_received(data)

    def eof_received(self):
        self.protocol.eof_received()


class USBMux(PlistProto):
    '''USBMux wraps a connection to the USBMux daemon.

    Use ``connect_to_usbmux`` or call ``connect`` on an instance of this
    class to connect to the daemon.

    Once connected, the ``attached`` attribute is populated with a dictionary
    keyed by an integer device id, and with a dictionary of values about the
    connected device.

    The ``attached`` dictionary is populated asynchronously and may be empty
    after ``connect`` returns.

    Subclasses of USBMux will have their ``device_attached`` and
    ``device_detached`` methods called as devices are made available through
    the connected mux.

    Alternatively call :meth:`wait_for_attach` to wait for a new device to
    be made available, or use the :meth:`attach_watcher` method to obtain
    a context manager to iterate over all devices as they connect and
    disconect.

    The ``connect`` call will open a TCP connection to a specific port
    on a specific device.  :meth:`connect_to_first` can be used if it doesn't
    matter which device is connected to, as long as the requested port is open.
    '''
    def __init__(self, loop, mux_socket_path=DEFAULT_SOCKET_PATH, mux_socket_port=DEFAULT_SOCKET_PORT):
        #: Currently attached devices, keyed by integer device_id
        self.attached = {}
        self.loop = loop
        self.mux_socket_path = mux_socket_path
        self.mux_socket_port = mux_socket_port
        self._attach_notify = QueueNotify(loop=loop)

    async def _connect_transport(self, protocol_factory):
        if sys.platform in ('win32', 'cygwin'):
            return await self.loop.create_connection(protocol_factory, host='127.0.0.1', port=self.mux_socket_port)
        else:
            result = await self.loop.create_unix_connection(protocol_factory, self.mux_socket_path)
            return result

    async def connect(self):
        '''Opens a connection to the USBMux daemon on the local machine.

        :func:`connect_to_usbmux` provides a convenient wrapper to this method.
        '''
        self._waiter = asyncio.Future(loop=self.loop)
        await self._connect_transport(lambda: self)
        await self._waiter

    def connection_made(self, transport):
        super().connection_made(transport)

        self.send_msg(
                MessageType='Listen',
                ClientVersionString='pyusbmux',
                ProgName='pyusbmux'
            )

    def connection_lost(self, exc):
        super().connection_lost(exc)

        if not self._waiter.done():
            self._waiter.set_exception(exc)

    def msg_received(self, msg):
        mt = msg.get('MessageType')

        if mt == 'Result':
            if msg['Number'] == 0:
                self._waiter.set_result(None)
            else:
                self._waiter.set_exception(ConnectionFailed())

        elif mt == 'Attached':
            device_id = msg['Properties']['DeviceID']
            self.attached[device_id] = msg['Properties']
            self.device_attached(device_id, msg['Properties'])
            self._attach_notify.notify((ACTION_ATTACHED, device_id, msg['Properties']))

        elif mt == 'Detached':
            device_id = msg['DeviceID']
            if device_id in self.attached:
                props = self.attached[device_id]
                del(self.attached[device_id])
                self._attach_notify.notify((ACTION_DETACHED, device_id, props))
            self.device_detached(device_id)

    async def connect_to_device(self, protocol_factory, device_id, port):
        '''Open a TCP connection to a port on a device.

        Args:
            protocol_factory (callable): A callable that returns an asyncio.Protocol implementation
            device_id (int): The id of the device to connect to
            port (int): The port to connect to on the target device
        Returns:
            (dict, asyncio.Transport, asyncio.Protocol): The device information,
                connected transport and protocol.
        Raises:
            A USBMuxError subclass instance such as ConnectionRefused
        '''
        waiter = asyncio.Future(loop=self.loop)
        connector = USBMuxConnector(device_id, port, waiter)
        transport, switcher = await self._connect_transport(lambda: _ProtoSwitcher(self.loop, connector))

        # wait for the connection to succeed or fail
        await waiter

        app_protocol = switcher.switch_protocol(protocol_factory)
        device_info = self.attached.get(device_id) or {}
        return device_info, transport, app_protocol

    async def wait_for_serial(self, serial, timeout=DEFAULT_MAX_WAIT):
        '''Wait for a device with the specified serial number to attach.

        Args:
            serial (string): Serial number of the device to wait for.
            timeout (float): The maximum amount of time in seconds to wait for a
                matching device to be connected.
                Set to None to wait indefinitely, or -1 to only check currently
                connected devices.
        Returns:
            int: The device id of the connected device
        Raises:
            asyncio.TimeoutError if the device with the specified serial number doesn't appear.
        '''
        timeout = Timeout(timeout)
        with self.attach_watcher(include_existing=True) as watcher:
            while not timeout.expired:
                action, device_id, info = await watcher.wait_for_next(timeout.remaining)
                if action != ACTION_ATTACHED:
                    continue
                if info['SerialNumber'].lower() == serial.lower():
                    return device_id

        raise asyncio.TimeoutError("No devices matching serial number found")

    async def connect_to_first_device(self, protocol_factory, port, timeout=DEFAULT_MAX_WAIT,
            include=None, exclude=None):
        '''Open a TCP connection to the first device that has the requested port open.

        Args:
            protocol_factory (callable): A callable that returns an asyncio.Protocol implementation.
            port (int): The port to connect to on the target device.
            timeout (float): The maximum amount of time to wait for a suitable device to be connected.
        Returns:
            (dict, asyncio.Transport, asyncio.Protocol): The device information,
                connected transport and protocol.
        Raises:
            asyncio.TimeoutError if no devices with the requested port become
                available in the specified time.
        '''
        with self.attach_watcher(include_existing=True) as watcher:
            timeout = Timeout(timeout)
            while not timeout.expired:
                action, device_id, info = await watcher.wait_for_next(timeout.remaining)
                if action != ACTION_ATTACHED:
                    continue
                if exclude is not None and device_id in exclude:
                    continue
                if include is not None and device_id not in include:
                    continue
                try:
                    return await self.connect_to_device(protocol_factory, device_id, port)
                except USBMuxError:
                    pass

        raise asyncio.TimeoutError("No available devices")

    async def wait_for_attach(self, timeout=None):
        '''Wait for the next device attachment event.

        Args:
            timeout (float): Maximum amount of time to wait for an event, or None for no timeout
        Returns:
            int: The device id that attached.
        Raises:
            asyncio.TimeoutError if no devices with the requested port become
                available in the specified time.
        '''
        timeout = Timeout(timeout)
        with self.attach_watcher() as watcher:
            while True:
                action, device_id, info = await watcher.wait_for_next(timeout.remaining)
                if action == ACTION_ATTACHED:
                    return device_id

    def attach_watcher(self, include_existing=False):
        '''Returns a context manager that will record and make available all attach/detach notifications.

        The context manager yields events consisting of (action, device_id, device_info) tuples,
        where ``action`` is either :const:`ACTION_ATTACHED` or :const:`ACTION_DETACHED`
        and ``device_info`` is a dictionary of information specific to that device,
        such as the serial number.

        Args:
            include_existing (bool): If True then a stream of fake attached events
                will be generated for all existing connected devices ahead of
                monitoring for newly attached devices.
        Returns:
            :class:`QueueNotifyCM`
        '''
        initial_data = None
        if include_existing:
            initial_data = [(ACTION_ATTACHED, device_id, info)
                    for (device_id, info) in self.attached.items()]
        return self._attach_notify.get_contextmanager(initial_data=initial_data)

    def device_attached(self, device_id, properties):
        pass

    def device_detached(self, device_id):
        pass


async def connect_to_usbmux(mux_socket_path=DEFAULT_SOCKET_PATH, mux_socket_port=DEFAULT_SOCKET_PORT, loop=None):
    '''Connect to a USBMux endpoint.

    Args:
        mux_socket_path (string) - The path of the Unix socket of the mux daemon (used on non Windows platforms)
        mux_socket_port (int) - The TCP port number of the mux daemon (used on Windows platforms)
        loop (asyncio.BaseLoop) - Event loop to connect on; defaults to the current active event loop
    Returns:
        USBMux instance
    Raises:
        Exception on connection refused or other error
    '''
    if loop is None:
        loop = asyncio.get_event_loop()

    mux = USBMux(loop, mux_socket_path=mux_socket_path, mux_socket_port=mux_socket_port)
    await mux.connect()
    return mux


class QueueNotify:
    '''Provide a context manager to queue and read asynchronous notifications.

    While the context manager is active, all notifications are queued and
    read by calling ``wait_for_next`` on the returned QueueNotifyCM
    object.  If none are available, then the method will wait for the specified
    amount of time for a new entry to arrive.

    Multiple context managers can be active concurrently receiving the same
    notifications.
    '''
    def __init__(self, loop=None):
        self.loop = loop
        self._active = set()

    def notify(self, value):
        for entry in self._active:
            entry._notify(value)

    def get_contextmanager(self, initial_data=None, max_qsize=None):
        ctx = QueueNotifyCM(self, initial_data=initial_data, max_qsize=max_qsize, loop=self.loop)
        self._active.add(ctx)
        return ctx

    def context_done(self, ctx):
        self._active.discard(ctx)


class QueueNotifyCM:
    '''Helper class for QueueNotify.'''
    def __init__(self, mgr, initial_data=None, max_qsize=None, loop=None):
        self.loop = loop
        self._mgr = mgr
        self._wake = None
        if initial_data is None:
            initial_data = []
        self._q = collections.deque(initial_data, max_qsize)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._mgr.context_done(self)
        return False

    def _notify(self, item):
        self._q.append(item)
        if self._wake is not None and not self._wake.done():
            self._wake.set_result(True)
            self._wake = None

    async def wait_for_next(self, timeout=None):
        '''Wait for the next available notification.

        Will return immediately if entries are already waiting to be read,
        else wait up to ``timeout`` seconds for a new entry to arrive.
        '''
        try:
            return self._q.popleft()
        except IndexError:
            pass
        self._wake = asyncio.Future(loop=self.loop)
        await asyncio.wait_for(self._wake, loop=self.loop, timeout=timeout)
        return self._q.popleft()


class Timeout:
    '''Helper class to track timeout state.'''
    def __init__(self, timeout=None):
        self.timeout = timeout
        self.start = time.time()

    @property
    def remaining(self):
        if self.timeout is None:
            return None
        return self.timeout - (time.time() - self.start)

    @property
    def expired(self):
        return self.timeout is not None and self.remaining <= 0
