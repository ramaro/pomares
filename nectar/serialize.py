"""contains several encoding/decoding/serialization functions with bson"""

from zlib import crc32
import bson
from struct import unpack
from collections import namedtuple

from config import chunk_size


def encode_chunk(fileobj, chunk_size=chunk_size, eol=''):
    """reads chunk_size bytes from fileobj,
    returns a bson representation of a chunk"""
    seek = fileobj.tell()
    buff = fileobj.read(chunk_size)
    if buff:
        return bson.dumps({'data': buff, 'seek': seek,
                          'data_crc32': crc32(buff) & 0xffffffff})+eol

    else:
        raise EOFError('reached EOF, nothing to encode')


def decode_chunk(buff):
    d = decode(buff)

    try:
        if type(d['data']) != str:
            raise DecodeError('data is not string type')

        if type(d['seek']) != int:
            raise DecodeError('seek is not int type')

        crc32_recvd_data = crc32(d['data']) & 0xffffffff
        if crc32_recvd_data != d['data_crc32']:
            raise DecodeError('crc: recvd_data_crc32=%d but crc32(data)=%d'
                              % (crc32_recvd_data, d['data_crc32']))

        return d

    except KeyError as err:
        raise DecodeError('can\'t get key %s' % err.message)


def encoded_size(buff):
    return unpack('<I', buff[:4])[0]


def decode(buff):
    try:
        d = bson.loads(buff)
        return d
    except KeyError:
        raise DecodeError("buff does not seem to be bson encoded")


def encode(dict_msg):
    if type(dict_msg) != dict:
        raise EncodeError("dict_msg needs to be a dictionary")

    return bson.dumps(dict_msg)


class EncodeError(Exception):
    pass


class DecodeError(Exception):
    pass

#protocol:

ChunkRequest = namedtuple('ChunkRequest',
                          ('tree', 'checksum', 'chunk_from', 'chunk_to'))
ChunkRequestType = ChunkRequest(tree=unicode,
                                checksum=unicode, chunk_from=int, chunk_to=int)
ChunkRequest = namedtuple(

ChunkReply = namedtuple('ChunkReply', ('data', 'seek', 'data_crc32'))
ChunkReplyType = ChunkReply(data=unicode, seek=int, data_crc32=int)

SetValuesRequest = namedtuple('SetValuesRequest', ('db', 'values',))
SetValuesRequestType = SetValuesRequest(db=unicode, values=dict)


class SetValuesRequestError(Exception):
    pass

ValuesRequest = namedtuple('Values', ('values',))
ValuesRequestType = ValuesRequest(values=dict)

ShareTreeRequest = namedtuple('ShareTreeRequest', ('tree', 'hashes'))
ShareTreeRequestType = ShareTreeRequest(tree=unicode, hashes=list)

ShareTreeFileRequest = namedtuple('ShareTreeFileRequest',
                                  ('tree', 'hash_meta'))
ShareTreeFileRequestType = ShareTreeFileRequest(tree=unicode, hash_meta=dict)

IOReadChunkRequest = namedtuple('IOReadChunkRequest',
                                ('filename', 'offset', 'nbytes'))
IOReadChunkRequestType = IOReadChunkRequest(filename=unicode,
                                            offset=int, nbytes=int)

SetPermsRequest = namedtuple('SetPermsRequest', ('tree', 'keysum', 'perms'))
SetPermsRequestType = SetPermsRequest(tree=unicode, keysum=unicode,
                                      perms=unicode)
