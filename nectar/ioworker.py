"""io workers for sendfile
Writer and Reader processes are spawned
and communication is done via Domain Socket"""

import os
import pickle
from struct import pack
import nectar.proto as proto
import nectar.config as config
#from gevent.server import StreamServer
#from gevent import socket

#fix request pickling:
import sys
sys.modules['nectar.proto'] = proto

#from utils import gevent_sendfile as sendfile

open_files = {}


def ioreadchunk_request(handler, req):
    print('ioreadchunk_request', req)

    f = open(req.filename, 'rb')
    offset = req.offset
    nbytes = req.nbytes

    handler.send_size(nbytes)

    total_sent = 0
    while total_sent < nbytes:
        try:
            offset, sent = sendfile(handler.fd, f.fileno(), offset, nbytes)
            print('sent', sent)
            if sent == 0:
                break  # EOF
            total_sent += sent
            nbytes -= total_sent
            #print 'total_sent, nbytes, offset'
            #print total_sent, nbytes, offset
        except OSError:
            raise

    f.close()

ROUTES = {'IOReadChunkRequest': ioreadchunk_request,
          'SomethingElse': None}


def io_worker(name):
    """start io worker"""
    ioserv = PomaresIOServer(name, path=config.sock_path)
    ioserv.run()


def io_reader():
    """returns a io reader (for handler use)"""
    return PomaresIOClient('reader')


class PomaresIOHandler:
    def __init__(self, _socket, address):
        self.socket = _socket
        self.fd = self.socket.fileno()
        self.loop()

    def send(self, data):
        size = len(data)
        msg_size = pack('<I', size)
        self.socket.send(msg_size)
        self.socket.send(data)

    def send_size(self, size):
                self.socket.send(pack('<I', size))

    def set_clientfd(self, fd):
        self.clientfd = fd

    def recv(self):
        # handlers recv pickled objects
        len_size = 4
        read_size = 1024
        buff = ''
        buff += self.socket.recv(len_size)
        #TODO real size shouldnt be more than a % extra of msg_size
        if not buff:
            return None
        msg_size = proto.encoded_size(buff)
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

        return pickle.loads(buff)

    def route(self, request):
        """routes internal io requests"""
        try:
            # get request name for pickling:
            req_key = request.__class__.__name__
            func = ROUTES[req_key]
            func(self, request)
        except KeyError:
            print('ignoring request [bad key]')
        except AttributeError:
            print('ignoring request [no key]')
        except IndexError:
            print('ignoring request [no key]')

    def loop(self):
        while True:
            req = self.recv()

            if not req:
                print('iobreaking')
                break

            print('got ioreq:', req)
            self.route(req)


class PomaresIOServer:
    def __init__(self, name, path='./'):
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sockname = os.path.join(path, '%s.sock' % name)
        if os.path.exists(sockname):
            os.remove(sockname)
        listener.bind(sockname)
        listener.listen(1)
        self.worker = StreamServer(listener, PomaresIOHandler)

    def run(self):
        self.worker.serve_forever()


class PomaresIOClient:
    def __init__(self, name, path=config.sock_path):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(os.path.join(path, "%s.sock" % name))
        self.fd = self.socket.fileno()

    def send(self, data):
        _data = pickle.dumps(data)
        size = len(_data)
        msg_size = pack('<I', size)
        self.socket.send(msg_size)
        self.socket.send(_data)

        return size

    def recv(self):
        len_size = 4
        read_size = 1024
        buff = ''
        buff += self.socket.recv(len_size)
        #TODO real size shouldnt be more than a % extra of msg_size
        if not buff:
            return None
        msg_size = proto.encoded_size(buff)
        #print "received msg_size", msg_size
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

        return buff


if __name__ == '__main__':
    print('starting io_worker as reader...')
    io_worker('reader')
