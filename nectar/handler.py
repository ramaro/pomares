from nacl.utils import random as new_nonce
from struct import pack
from proto import encode, decode, compress_buff, decompress_buff, encoded_size

from nacl.public import Box


class Handler():
    def __init__(self, socket, address):
        #print 'New connection from %s:%s' % address
        self.socket = socket
        self.address = address
        self.fd = socket.fileno()

    def send(self, data, encrypt=True, wait=False, compress=True):
        _data = ''
        if encrypt:
            _data = self.box.encrypt(encode(data), new_nonce(Box.NONCE_SIZE))
        else:
            _data = encode(data)
        #print 'msg_size is', len(_data)
        if compress:
            _data = compress_buff(_data)
        if wait:
            self.socket.wait_write(self.fd)
        self.socket.send(pack('<I', len(_data))+_data)

    def recv(self, decrypt=True, my_box=False, wait=False, decompress=True):
        buff = ''
        len_size = 4  # 4 initial bytes for the msg length
        read_size = 1024
        remaining_bytes = 0

        if wait:
            self.socket.wait_read(self.fd)
        buff += self.socket.recv(len_size)

        #TODO real size shouldnt be more than a % extra of msg_size
        if not buff:
            return None
        #print len(buff)
        msg_size = encoded_size(buff)
        #print 'msg_size is', msg_size
        remaining_bytes = msg_size
        buff = buff[len_size:]

        while remaining_bytes > 0:
            if (msg_size - read_size) >= 0:
                _buff = self.socket.recv(read_size)
                buff += _buff
                remaining_bytes -= len(_buff)
            else:
                _buff = self.socket.recv(remaining_bytes)
                buff += _buff
                remaining_bytes -= len(_buff)

                if remaining_bytes == 0:
                    break

        if decompress:
            buff = decompress_buff(buff)
        if decrypt:
            if my_box:
                return decode(self.my_box.decrypt(buff))

            return decode(self.box.decrypt(buff))
        else:
            return decode(buff)

    def send_request(self, request, encrypt=True, wait=False):
        #req_dict = request._asdict()
        #self.send({request.__class__.__name__: req_dict}, encrypt, wait)
        self.send(request, encrypt, wait)


class BadHandshake(Exception):
    pass
