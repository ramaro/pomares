from msgpack import packb, unpackb
from collections import namedtuple
from zlib import compress, decompress
import struct

ChunkRequest = namedtuple('ChunkRequest', ('tree', 'checksum', 'chunk_from', 'chunk_to'))
ChunkReply = namedtuple('ChunkReply', ('data', 'seek', 'data_crc32'))
SetValuesRequest = namedtuple('SetValuesRequest', ('db', 'values',))
ValuesRequest = namedtuple('Values', ('values',))
ShareTreeRequest = namedtuple('ShareTreeRequest', ('tree', 'hashes'))
ShareTreeFileRequest = namedtuple('ShareTreeFileRequest', ('tree', 'hash_meta'))
IOReadChunkRequest = namedtuple('IOReadChunkRequest', ('filename', 'offset', 'nbytes'))
SetPermsRequest = namedtuple('SetPermsRequest', ('tree', 'keysum', 'perms'))
Ack = namedtuple('Ack', ('value',))
PubKeyReply = namedtuple('PubKeyReply', ('key',))

msg_dict = {'ChunkRequest':(0, ChunkRequest),
            'ChunkReply':(1, ChunkReply),
            'SetValuesRequest':(2, SetValuesRequest),
            'SetPermsRequest':(3, SetPermsRequest),
            'ValuesRequest':(4, ValuesRequest),
            'ShareTreeRequest':(5, ShareTreeRequest),
            'ShareTreeFileRequest':(6, ShareTreeFileRequest),
            'IOReadChunkRequest':(7, IOReadChunkRequest),
            'SetPermsRequest':(8, SetPermsRequest),
            'Ack':(9, Ack),
            'PubKeyReply':(10, PubKeyReply)
            }
msg_dict_rev = dict((v[0],v[1]) for k,v in msg_dict.items())

def pack_proto(msg):
    msg_t = msg.__class__.__name__
    return tuple((msg_dict[msg_t][0],) + tuple((getattr(msg, f) for f in msg._fields)))

def unpack_proto(msg):
    msg_t = msg_dict_rev[msg[0]]
    return msg_t(*msg[1:])

def encode(msg):
    pack_proto(msg)
    return packb(pack_proto(msg))

def decode(msg_buff):
    return unpack_proto(unpackb(msg_buff))

def encoded_size(buff):
    return struct.unpack('<I', buff[:4])[0]

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
