from nacl.public import PublicKey, Box
from nectar.proto import IOReadChunkRequest, Ack, PomaresProtocol, BadHandshake, PomaresHandler
from nectar.proto import decompress_buff, compress_buff, encode, decode
from nectar.config import pub_key, priv_key  # allowed_keys
from nectar.utils import load_key, pubkey_sum, generate_keys
from nectar.auth import Auth, AuthDeniedError, NotAllowedError
from nectar.ioworker import io_reader
from nectar.store import HashBasenames, TreeHashes, SumAllow
from pprint import pprint
import logging
import sys

import asyncio

#TODO use a decorator instead here:
def chunk_request(handler, req):
    print('I am a chunk request! with args:', req)

    #grab file params from args and send it to ioreader:
    ioreq = IOReadChunkRequest(filename='/tmp/some.random.file',
                               offset=0, nbytes=40035719)
    #handler.send({'data': buff})
    # this should partition the request into X IOReadChunkRequest requests
    # and read / send back one by one

    handler.ioreader.send(ioreq)
    print('receiving...')
    buff = handler.ioreader.recv()
    print('got a chunk request len reply:', len(buff))


#TODO use a decorator instead here:
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


#TODO use a decorator instead here:
def setperms_request(handler, args):
    if not handler.auth.is_admin:
        raise NotAllowedError()

    sa = SumAllow(args['tree'])
    sa[args['keysum']] = args['perms']


#TODO use a decorator instead here:
def setvalues_request(handler, args):
    print('I am a setvalues_request with args:')
    pprint(args)
    pass


#TODO use a decorator instead here:
def pubkey_reply(handler, args):
    pass

#TODO use a decorator instead here:
ROUTES = {'ChunkRequest': chunk_request,
          'SetValuesRequest': setvalues_request,
          'SetPermsRequest': setperms_request,
          'ShareTreeFileRequest': sharetree_request,
          'PubKeyReply': pubkey_reply,
          }


class PomaresServer:
    def __init__(self, pub_key, priv_key, address='0.0.0.0', port=8080):
        self.pub_key = load_key(pub_key, key_type='pub')
        self.priv_key = load_key(priv_key, key_type='priv')
        self.routes = ROUTES
        PomaresProtocol.server_priv_key = self.priv_key
        PomaresProtocol.pub_key = None

        #box with server's own pair (to recv data with own pubkey):
        PomaresProtocol.my_box = Box(self.priv_key, self.pub_key)
        PomaresProtocol.route = self.route
        self.loop = asyncio.get_event_loop()
        self.server = self.loop.create_server(PomaresProtocol, address, port)

    def do_handshake(self, handler, msg):
        try:
            client_pubkey = decode(msg)
            handler.pub_key = PublicKey(client_pubkey.key)
            handler.auth = Auth(pubkey_sum(self.pub_key))
            handler.box = Box(self.server.priv_key, self.pub_key)
            #handler.send(Ack('OK')) TODO
            handler.handshaked = True
            print("capabilities:", handler.auth.capabilities)
            print("handshake OK")
            #self.handler.ioreader = io_reader() TODO
        # yes, ALL exceptions will raise BadHandshake
        except:
            raise BadHandshake()

    def route(self, handler, msg):
        print('(route) I am routing this msg:', msg)
        try:
            msg = decompress_buff(msg)
            print('(route) decompressed msg:', msg)

            if not handler.handshaked:
                # receive client's pubkey with my_box
                msg = self.my_box.decrypt(msg)
                # at this point we can only expect PubKeyReply 
                self.do_handshake(handler, msg)
            else:
                msg = handler.box.decrypt(msg)
            
                request = decode(msg)
                req_key = request.keys()[0]
                func = self.routes[req_key]

                # treat func exceptions separately
                try:
                    func(handler, request[req_key])
                except Exception as err:
                    print("got route func exception:", err)
                    raise

        except KeyError:
            print('ignoring request [bad key]')
        except AttributeError:
            print('ignoring request [no key]')
        except IndexError:
            print('ignoring request [no key]')


    
    def run(self):
        session = self.loop.run_until_complete(self.server)
        print('serving on {}'.format(session.sockets[0].getsockname()))
        self.loop.run_forever()


def start_server():
    #generate_keys()
    server = PomaresServer(pub_key, priv_key)
    server.run()


if __name__ == '__main__':
    if sys.argv[1] == 'server':
        start_server()
    elif sys.argv[1] == 'client':
        loop = asyncio.get_event_loop()
        payload = sys.argv[2]
        payload = bytes(payload.encode())
        print('input size: {}'.format(len(payload)))
        payload = compress_buff(payload)
        print('payload size: {}'.format(4+len(payload)))
        server_prot = PomaresProtocol(payload)
        loop.run_until_complete(loop.create_connection(lambda: server_prot, host='127.0.0.1', port=8080))
        loop.run_forever()
        loop.close()
