import asyncio


from nacl.utils import random as new_nonce
from struct import unpack, pack
#from proto import encode, decode, compress_buff, decompress_buff, encoded_size

from nacl.public import Box
import sys



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    if sys.argv[1] == 'server':
        coro = loop.create_server(PomaresProtocol, '127.0.0.1', 8888)
        server = loop.run_until_complete(coro)
        print('serving on {}'.format(server.sockets[0].getsockname()))
        loop.run_forever()
    elif sys.argv[1] == 'client':
        payload = sys.argv[2]
        print('payload size: {}'.format(4+len(payload)))
        server_prot = PomaresProtocol(payload)
        loop.run_until_complete(loop.create_connection(lambda: server_prot, host='127.0.0.1', port=8888))

    """
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
    """


