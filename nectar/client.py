from config import key_path
from crypto import CryptoBox, SecretBox, load_key
from os.path import exists as path_exists, basename, dirname

import asyncio

from nectar.proto import IOReadChunkRequest, Ack, PomaresProtocol, BadHandshake, PomaresHandler, PubKeyReply
from nectar.proto import decompress_buff, compress_buff, encode, decode
import logging

ROUTES = {}

class PomaresClient:
    def __init__(self, address, key_path, server_pub_key):
        self.keyobj = load_key(key_path)
        logging.debug("client init_box pk: {}".format(self.keyobj.pk))
        logging.debug("client init_box sk: {}".format(self.keyobj.sk))
        PomaresProtocol.route = self.route
        self.host, self.port = address # TODO make it a list for more connections

        self.do_handshake_init()

    def do_handshake_init(self):
        logging.debug('(route) do_handshake_init()')
        # send my pubkey to server
        handshk_payload = compress_buff(encode(PubKeyReply(self.keyobj.pk)))
        self.client_prot = PomaresProtocol(handshk_payload)


    def do_handshake(self, handler, msg):
        logging.debug('(route) do_handshake()')
        # expect server to send secret key to init_box
        handler.init_box = CryptoBox(self.keyobj)
        handler.init_box.box_with(server_pub_key)

        # receive server secretkey
        msg = handler.init_box.decrypt(msg)
        msg = decode(msg)
        handler.box = SecretBox(key=msg.key)
        handler.handshaked = True
        logging.debug('HANDSHAKED2')

        # XXX send test msg
        logging.debug('(route) send test msg')
        new_msg = encode(Ack('acking this msg'))
        new_msg = handler.box.encrypt(new_msg)
        handler.send_data(compress_buff(new_msg))


    def route(self, handler, msg):
        logging.debug('(route) I am routing this msg: {}'.format(msg))
        try:
            msg = decompress_buff(msg)
            logging.debug('(route) decompressed msg: {}'.format(msg))
            if not handler.handshaked:
                logging.debug('(route) decoded msg: {}'.format(msg))
                # at this point we can only expect PubKeyReply 
                self.do_handshake(handler, msg)
            else:
                msg = handler.box.decrypt(msg)
            
                request = decode(msg)
                logging.debug('(route) got request: {}'.format(request))
  
                # XXX test
                new_msg = encode(Ack('take that'))
                new_msg = handler.box.encrypt(new_msg)
                handler.send_data(compress_buff(new_msg))
        except Exception as err:
            logging.debug('!!!! ignoring request [bad key] {}'.format(err))
            raise

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(loop.create_connection(lambda: self.client_prot, self.host, self.port))
        loop.run_forever()
        loop.close() 
    

if __name__ == '__main__':
    server_pub_key = load_key(key_path+'/my.key')
    server_pub_key = server_pub_key.pk
    my_key = key_path+'/my_other.key'
    c = PomaresClient(('127.0.0.1', 8080), my_key, server_pub_key)
    c.run()
