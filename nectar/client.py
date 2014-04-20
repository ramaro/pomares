from gevent.socket import create_connection 
from gevent.queue import Queue
from gevent import Greenlet
from config import pub_key, priv_key
from nacl.public import Box
from utils import load_key
from store import FileState
from handler import Handler, BadHandshake
from proto import ChunkRequest, Ack, PubKeyReply, encoded_size
from os.path import exists as path_exists, basename, dirname
import struct

#TODO treat server replies, acks, here
# so we can continue or raise exceptions like SetValuesRequestError
ROUTES = {}


class PomaresClientHandler(Handler):
    def __init__(self, address, pub_key, priv_key, host_pub_key, task_queue,
                 init_only=False):
        self.socket = create_connection(address)
        print 'init', self.socket
        Handler.__init__(self, self.socket, address)
        self.pub_key = load_key(pub_key, 'pub')
        self.priv_key = load_key(priv_key, 'priv')
        self.box = Box(self.priv_key, host_pub_key)
        self.task_queue = task_queue

        self.init_handshake()

        if not init_only:
            self.loop()

    def init_handshake(self):
        """init_handshake only sends the client's pub_key"""
        try:
            #send my pub key
            self.send(PubKeyReply(self.pub_key.encode()))
            #self.send({'pub': self.pub_key.encode()})
            ack = self.recv()
            if ack.value != 'OK':
                raise BadHandshake
        except ValueError:
            raise BadHandshake
        except KeyError:
            raise BadHandshake
        except struct.error:
            raise BadHandshake

    def loop(self):
        while True:
            if self.task_queue.empty():
                #TEMP TEMP TEMP
                print 'empty queue, quitting'
                break
            print 'waiting'
            task = self.task_queue.get()
            print 'got task', task
            #func, params = task
            #func = getattr(self, func)
            #func(*params)
            self.request(task)

    def prepare_file(self):
        if not path_exists(self.save_to):
            self.f = open(self.save_to, 'w')
            self.f_state = FileState(basename(self.save_to),
                                     dirname(self.save_to))
        else:
            raise Exception("%s exists, quitting." % (self.save_to,))
            quit(1)

    def request_chunk(self, tree, checksum, chunk_from, chunk_to):
        print 'chunk_request'
        req = ChunkRequest(tree, checksum, chunk_from, chunk_to)
        self.send_request(req)
        print 'send:', req

    def request(self, req):
        print 'sending req:', req
        self.send_request(req)


def new():
    task_queue = Queue()
    task_queue.put(ChunkRequest(tree='my_tree',
                                checksum='my_hash',
                                chunk_from=0, chunk_to=666))
    #task_queue.put(('request_chunk', ('my_tree', 'my_hash', 0, 666)))
    PomaresClientHandler(("127.0.0.1", 8080),
                         pub_key, priv_key,
                         load_key(pub_key, 'pub'), task_queue)

"""
admin:
push admin data as dictionaries. whatever you push, gets overwritten.
seems generic enough as all data is a key/val pair anyway
push chunk_sized dicts, to save buffering memory.
should start with file info (chksum,size,path,name) code first
"""

if __name__ == '__main__':
    #get(None, '/tmp/bla.out')
    #post('I am some data')

    #TODO prepare new file handles and pass it to the client greenlets

    clients = [Greenlet.spawn(lambda: new()) for g in xrange(0, 5)]
    print 'test'
    for c in clients:
        c.join()
