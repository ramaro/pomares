from msgpack import packb, unpackb
from collections import namedtuple
from zlib import compress, decompress
from struct import pack, unpack
import asyncio
from nectar.utils import logger
from concurrent.futures import ThreadPoolExecutor

Ack = namedtuple('Ack', ('value',))
PubKeyReply = namedtuple('PubKeyReply', ('key',))
ImportTreeRequest = namedtuple('ImportTreeRequest', ('tree'))
IOReadChunkRequest = namedtuple('IOReadChunkRequest',
                                ('filename', 'offset', 'nbytes'))

msg_dict = {'Ack': (1, Ack),
            'PubKeyReply': (2, PubKeyReply),
            'ImportTreeRequest': (3, ImportTreeRequest),
            'IOReadChunkRequest': (4, IOReadChunkRequest),
            }
# Reverse lookup:
msg_dict_rev = dict((v[0], v[1]) for k, v in msg_dict.items())


class PomaresHandler():
    def __init__(self, transport):
        self.transport = transport
        self.handshaked = False
        self.io_transport = None

    def send_data(self, payload):
        payload_size = len(payload)
        payload = pack('<I{:d}s'.format(payload_size), payload_size, payload)
        logger.debug('sending payload ({} bytes): {}'.format(payload_size,
                                                             payload))
        self.transport.write(payload)


class PomaresAdminHandler():
    def __init__(self, transport):
        self.transport = transport
        self.index_writer = None

    def send_data(self, payload):
        self.transport.write(bytes('{}\n'.format(payload).encode()))


class PomaresAdminProtocol(asyncio.Protocol):
    def __init__(self, payload=None):
        self.payload = payload

    def connection_made(self, transport):
        logger.debug('admin connection made')
        self.handler = PomaresAdminHandler(transport)
        self.data_buffer = bytearray()
        self.data_buffer_size = 0

        if self.payload:
            self.handler.send_data(self.payload)
            self.payload = None

    def data_received(self, data):
        logger.debug('received admin data: {}'.format(data))
        # connection is made
        self.data_buffer.extend(data)

        for line in self.data_buffer.splitlines(keepends=True):
            if line.endswith(b'\n'):
                self.route(self.handler, line[:-1])
            else:
                self.data_buffer = line

    def route(self, handler, msg):
        logger.debug('got admin message: {}'.format(msg))

    def connection_lost(self, exc):
        logger.debug('admin lost connection')
        # commit index writer here
        if self.handler.index_writer:
            self.handler.index_writer.commit()
            logger.debug('(admin handler) committed data in index_writer {}'.
                         format(id(self.handler.index_writer)))


class PomaresProtocol(asyncio.Protocol):
    def __init__(self, payload=None, handler_type=PomaresHandler):
        self.payload = payload
        self.header_size = 4
        self.handler_type = handler_type

    def connection_made(self, transport):
        self.handler = self.handler_type(transport)
        self.data_buffer = bytearray()
        self.data_buffer_size = 0
        self.msg_size = 0

        logger.debug('connection made')
        if self.payload:
            self.handler.send_data(self.payload)
            self.payload = None

    def data_received(self, data):
        logger.debug('received data: {}'.format(data))

        # connection is made
        self.data_buffer.extend(data)
        self.data_buffer_size += len(data)

        if (not self.msg_size) and (self.data_buffer_size >= self.header_size):
            self.msg_size = self.encoded_size(self.data_buffer)
            logger.debug('set msg_size to {}'.format(self.msg_size))

        logger.debug('data_buffer_size: {}'.format(self.data_buffer_size))
        logger.debug('msg_size: {}'.format(self.msg_size))

        if (self.data_buffer_size - self.header_size) >= self.msg_size:
            # got a complete msg, do stuff with it:
            logger.debug('got a complete msg, call route')
            self.route(self.handler, data[self.header_size:])

            # reset for next msg
            logger.debug('## RESET ##')
            self.msg_size = 0
            self.data_buffer = bytearray(data[self.data_buffer_size:])
            self.data_buffer_size = len(self.data_buffer)

    def connection_lost(self, exc):
        logger.debug('lost connection')

    def encoded_size(self, data):
        "return size based on header_size (in bytes)"
        return unpack('<I', data[:self.header_size])[0]

    def route(self, handler, msg):
        logger.debug('got message: {}'.format(msg))


class PomaresIOHandler(PomaresHandler):
    def __init__(self, transport):
        super().__init__(transport)
        del self.handshaked
        del self.io_transport


class PomaresIOProtocol(PomaresProtocol):
    def __init__(self, payload=None, workers=4):
        super().__init__(payload, handler_type=PomaresIOHandler)
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def connection_made(self, transport):
        super().connection_made(transport)

    def route(self, handler, msg):
        logger.debug('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> got message: {}'.format(msg))


def pack_proto(msg):
    msg_t = msg.__class__.__name__
    return tuple((msg_dict[msg_t][0],) +
                 tuple((getattr(msg, f) for f in msg._fields)))


def unpack_proto(msg):
    msg_t = msg_dict_rev[msg[0]]
    return msg_t(*msg[1:])


def encode(msg):
    return packb(pack_proto(msg))


def decode(msg_buff):
    return unpack_proto(unpackb(msg_buff))


def compress_buff(buff):
    return compress(buff)


def decompress_buff(buff):
    return decompress(buff)


class EncodeError(Exception):
    pass


class DecodeError(Exception):
    pass


class SetValuesRequestError(Exception):
    pass


class BadHandshake(Exception):
    pass
