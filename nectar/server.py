from crypto import CryptoBox, SecretBox, PublicKey, SecretKey, load_key, pubkey_sum, generate_keys
from nectar.proto import IOReadChunkRequest, Ack, PomaresProtocol, BadHandshake, PomaresHandler, PubKeyReply
from nectar.proto import decompress_buff, compress_buff, encode, decode
from nectar.config import key_path # allowed_keys
#from nectar.auth import Auth, AuthDeniedError, NotAllowedError
from nectar.ioworker import io_reader
from nectar.store import HashBasenames, TreeHashes, SumAllow
from pprint import pprint
import logging
import sys
import copy

import asyncio

def pubkey_reply(handler, args):
        print('running pubkey_reply!')


#TODO use a decorator instead here:
ROUTES = {
          'PubKeyReply': pubkey_reply,
          }

class PomaresServer:
    def __init__(self, key_path, address='0.0.0.0', port=8080):
        self.keyobj = load_key(key_path)
        self.routes = ROUTES

        PomaresProtocol.route = self.route
        self.loop = asyncio.get_event_loop()
        self.server = self.loop.create_server(PomaresProtocol, address, port)

    def route(self, handler, msg):
        logging.debug('(route) I am routing this msg: {}'.format(msg))
        try:
            msg = decompress_buff(msg)
            logging.debug('(route) decompressed msg: {}'.format(msg))
            if not handler.handshaked:
                msg = decode(msg)
                logging.debug('(route) decoded msg: {}'.format(msg))
                # at this point we can only expect PubKeyReply 
                self.do_handshake(handler, msg)
            else:
                msg = handler.box.decrypt(msg)
                request = decode(msg)
                logging.debug('(route) decrypted and decoded msg: {}'.format(request))

                #func = self.routes[req_key]
                
        except Exception as err:
            logging.info('ignoring request [bad key] {}'.format(err))
            raise

    def do_handshake(self, handler, msg):
        logging.debug('(route) do_handshake()')
        try:
            # receive client pubkey and create my init_box
            handler.init_box = CryptoBox(self.keyobj)
            logging.debug("server init_box pk: {}".format(self.keyobj.pk))
            logging.debug("server init_box sk: {}".format(self.keyobj.sk))

            # init box with client's pubkey
            handler.init_box.box_with(msg.key) 

            # create and send secret
            handler.box = SecretBox()
            sk_msg = encode(PubKeyReply(handler.box.sk)) 
            sk_msg = handler.init_box.encrypt(sk_msg)
            handler.send_data(compress_buff(sk_msg)) 

            handler.handshaked = True
            logging.info('HANDSHAKED1')
        except:
            raise BadHandshake()

    
    def run(self):
        session = self.loop.run_until_complete(self.server)
        logging.debug('serving on {}'.format(session.sockets[0].getsockname()))
        self.loop.run_forever()


def start_server():
    #generate_keys(key_path)
    server = PomaresServer(key_path+'/my.key')
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
