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
    'ConnectionRefused', 'ConnectionFailed', 'USBMux', 'connect_to_usbmux')

import asyncio
import plistlib
import socket
import struct
import sys
import time


DEFAULT_SOCKET_PATH = '/var/run/usbmuxd'
DEFAULT_SOCKET_PORT = 27015
DEFAULT_MAX_WAIT = 2

PLIST_VERSION = 1


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

    Alternatively call ``wait_for_attach`` to wait for a new device to
    be made available.

    The ``connect`` call will open a TCP connection to a specific port
    on a specific device.  ``connect_to_first`` can be used if it doesn't
    matter which device is connected to, as long as the requested port is open.
    '''
    def __init__(self, loop, mux_socket_path=DEFAULT_SOCKET_PATH, mux_socket_port=DEFAULT_SOCKET_PORT):
        #: Currently attached devices, keyed by integer device_id
        self.attached = {}
        self.loop = loop
        self.mux_socket_path = mux_socket_path
        self.mux_socket_port = mux_socket_port
        self._attach_waiters = set()

    async def _connect_transport(self, protocol_factory):
        if sys.platform in ('win32', 'cygwin'):
            return await self.loop.create_connection(protocol_factory, host='127.0.0.1', port=self.mux_socket_port)
        else:
            result = await self.loop.create_unix_connection(protocol_factory, self.mux_socket_path)
            return result

    async def connect(self):
        '''Opens a connection to the USBMux daemon on the local machine.

        connect_to_usbmux provides a convenient wrapper to this method.
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
            for fut in self._attach_waiters:
                fut.set_result(device_id)
            self._attach_waiters.clear()

        elif mt == 'Detached':
            device_id = msg['DeviceID']
            if device_id in self.attached:
                del(self.attached[device_id])
            self.device_detached(device_id)

    async def connect_to_device(self, protocol_factory, device_id, port):
        '''Open a TCP connection to a port on a device.

        Args:
            protocol_factory (callable): A callable that returns an asyncio.Protocol implementation
            device_id (int): The id of the device to connect to
            port (int): The port to connect to on the target device
        Returns:
            (asyncio.Transport, asyncio.Protocol) - The connected transport and protocol
        Raises:
            A USBMuxError subclass instance such as ConnectionRefused
        '''
        waiter = asyncio.Future(loop=self.loop)
        connector = USBMuxConnector(device_id, port, waiter)
        transport, switcher = await self._connect_transport(lambda: _ProtoSwitcher(self.loop, connector))

        # wait for the connection to succeed or fail
        await waiter

        app_protocol = switcher.switch_protocol(protocol_factory)
        return transport, app_protocol

    async def connect_to_first_device(self, protocol_factory, port, max_wait=DEFAULT_MAX_WAIT):
        '''Open a TCP connection to the first device that has the requested port open.

        Args:
            protocol_factory (callable): A callable that returns an asyncio.Protocol implementation
            port (int): The port to connect to on the target device
            max_wait (float): The maximum amount of time to wait for a suitable device to be connected
        Returns:
            (asyncio.Transport, asyncio.Protocol) - The connected transport and protocol
        Raises:
            asyncio.TimeoutError - If no devices with the requested port become available in the specified time
        '''
        seen = set()

        while max_wait is None or max_wait > 0:
            ids = set(self.attached.keys()) - seen
            for device_id in ids:
                seen.add(device_id)
                try:
                    return await self.connect_to_device(protocol_factory, device_id, port)
                except USBMuxError:
                    pass
            start = time.time()
            await self.wait_for_attach(max_wait)
            max_wait -= (time.time() - start)

        raise asyncio.TimeoutError("No available devices")

    async def wait_for_attach(self, timeout=None):
        '''Wait for the next device attachment event

        Args:
            timeout (float): Maximum amount of time to wait for an event, or None for no timeout
        Returns:
            int: The device id that was connected
        Raises:
            asyncio.TimeoutError
        '''
        fut = asyncio.Future(loop=self.loop)
        self._attach_waiters.add(fut)
        try:
            return await asyncio.wait_for(fut, loop=self.loop, timeout=timeout)
        finally:
            self._attach_waiters.discard(fut)

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
