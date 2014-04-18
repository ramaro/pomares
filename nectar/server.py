from gevent.server import StreamServer
from nacl.public import PublicKey, Box
from handler import Handler, BadHandshake
from serialize import IOReadChunkRequest
from config import pub_key, priv_key  # allowed_keys
from utils import load_key, pubkey_sum
from auth import Auth, AuthDeniedError, NotAllowedError
from ioworker import io_reader
from store import HashBasenames, TreeHashes, SumAllow
from pprint import pprint
import logging


def chunk_request(handler, req):
    print 'I am a chunk request! with args:', req

    #grab file params from args and send it to ioreader:
    ioreq = IOReadChunkRequest(filename='/Users/ramaro/Downloads/Skype_6.5.0.443.dmg',
                               offset=0, nbytes=40035719)
    #handler.send({'data': buff})
    # this should partition the request into X IOReadChunkRequest requests
    # and read / send back one by one

    handler.ioreader.send(ioreq)
    print 'receiving...'
    buff = handler.ioreader.recv()
    print 'got a chunk request len reply:', len(buff)


def sharetree_request(handler, args):
    if not handler.auth.is_admin:
        raise NotAllowedError()

    hash_meta = args['hash_meta']
    basename = hash_meta.keys()[0]

    # create HashBasenames with hash as filename:
    hb = HashBasenames(hash_meta[basename]['hash'])
    hb[basename] = hash_meta[basename]

    # create TreeHashes (list of keys (hash)
    th = TreeHashes(args['tree'])
    tree_val = {'tree_path': hash_meta[basename]['tree_path'],
                'path': hash_meta[basename]['path']}

    # save path and tree_path as the same file can live elsewhere
    # TODO check if already exists and replace/append in list
    th[hash_meta[basename]['hash']] = tree_val


def setperms_request(handler, args):
    if not handler.auth.is_admin:
        raise NotAllowedError()

    sa = SumAllow(args['tree'])
    sa[args['keysum']] = args['perms']


def setvalues_request(handler, args):
    print 'I am a setvalues_request with args:'
    pprint(args)
    pass

ROUTES = {'ChunkRequest': chunk_request,
          'SetValuesRequest': setvalues_request,
          'SetPermsRequest': setperms_request,
          'ShareTreeFileRequest': sharetree_request,
          }


class PomaresHandler(Handler):
    def __init__(self, socket, address):
        Handler.__init__(self, socket, address)
        try:
            self.do_handshake()
            print "capabilities:", self.auth.capabilities
            print "handshake OK"
            self.ioreader = io_reader()
            self.loop()
        except BadHandshake:
            print 'bad handshake, closing'
            return
        except AuthDeniedError:
            print 'auth denied, closing'
            return

    def do_handshake(self):
        """"reads client's key and replies with auth ack"""
        key_dict = self.recv(my_box=True)

        try:
            #==check auth here==
            self.pub_key = PublicKey(key_dict['pub'])
            self.auth = Auth(pubkey_sum(self.pub_key))
            self.box = Box(self.server_priv_key, self.pub_key)
            self.send({'ack': 'OK'})
        except KeyError:
            raise BadHandshake()
        except ValueError:
            raise BadHandshake()
        except TypeError:
            raise BadHandshake()

    def route(self, request):
        """routes requests"""
        try:
            req_key = request.keys()[0]
            func = ROUTES[req_key]

            # treat func exceptions separately
            try:
                func(self, request[req_key])
            except Exception, err:
                print "got route func exception:", err
                raise

        except KeyError:
            print 'ignoring request [bad key]'
        except AttributeError:
            print 'ignoring request [no key]'
        except IndexError:
            print 'ignoring request [no key]'

    def loop(self):
        while True:
            req = self.recv()
            print 'got req:', req
            self.route(req)
            if not req:
                print 'connection closed'
                break


class PomaresServer:
    def __init__(self, pub_key, priv_key, address='0.0.0.0', port=8080):
        self.pub_key = load_key(pub_key, key_type='pub')
        self.priv_key = load_key(priv_key, key_type='priv')
        PomaresHandler.server_priv_key = self.priv_key
        PomaresHandler.pub_key = None
        #box with server's own pair (to recv data w/ own pubkey):
        PomaresHandler.my_box = Box(self.priv_key, self.pub_key)
        self.server = StreamServer((address, port), PomaresHandler)

    def run(self):
        self.server.serve_forever()


def start_server():
    server = PomaresServer(pub_key, priv_key)
    server.run()

if __name__ == '__main__':
    start_server()
