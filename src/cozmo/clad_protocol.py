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

__all__ = []


import asyncio
import struct
import sys

from . import logger_protocol

LOG_ALL = 'all'

if sys.byteorder != 'little':
    raise ImportError("Cozmo SDK doesn't support byte order '%s' - contact Anki support to request this", sys.byteorder)


class CLADProtocol(asyncio.Protocol):
    '''Low level CLAD codec'''

    clad_decode_union = None
    clad_encode_union = None
    _clad_log_which = None

    def __init__(self):
        super().__init__()

        self._buf = bytearray()

    def connection_made(self, transport):
        self.transport = transport
        logger_protocol.debug('Connected to transport')

    def connection_lost(self, exc):
        logger_protocol.debug("Connnection to transport lost: %s" % exc)

    def data_received(self, data):
        self._buf.extend(data)
        # pull clad messages out

        while True:
            msg = self.decode_msg()
            if not msg:
                return
            name = msg.tag_name
            if self._clad_log_which is LOG_ALL or (self._clad_log_which is not None and name in self._clad_log_which):
                logger_protocol.debug('RECV  %s',  msg._data)
            self.msg_received(msg)

    def decode_msg(self):
        if len(self._buf) < 2:
            return None

        # TODO: handle error
        # messages are prefixed by a 2 byte length
        msg_size = struct.unpack_from('H', self._buf)[0]
        if len(self._buf) < 2 + msg_size:
            return None

        buf, self._buf = self._buf[2:2+msg_size], self._buf[2+msg_size:]

        try:
            return self.clad_decode_union.unpack(buf)
        except ValueError as e:
            logger_protocol.warn("Failed to decode CLAD message for buflen=%d: %s", len(buf), e)

    def eof_received(self):
        logger_protocol.info("EOF received on connection")

    def send_msg(self, msg, **params):
        if self.transport.is_closing():
            return
        name = msg.__class__.__name__
        msg = self.clad_encode_union(**{name: msg})
        msg_buf = msg.pack()
        msg_size = struct.pack('H', len(msg_buf))
        self.transport.write(msg_size)
        self.transport.write(msg_buf)
        if self._clad_log_which is LOG_ALL or (self._clad_log_which is not None and name in self._clad_log_which):
            logger_protocol.debug("SENT %s", msg)

    def send_msg_new(self, msg):
        name = msg.__class__.__name__
        return self.send_msg(name, msg)

    def msg_received(self, msg):
        pass

