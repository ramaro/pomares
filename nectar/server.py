from nectar.crypto import CryptoBox, SecretBox, PublicKey, SecretKey, load_key, pubkey_sum, generate_keys
from nectar.proto import IOReadChunkRequest, Ack, PomaresServerProtocol, BadHandshake, PomaresHandler, PubKeyReply
from nectar.proto import PomaresAdminProtocol
from nectar.proto import decompress_buff, compress_buff, encode, decode
from nectar.config import key_path, admin_sock_file
from nectar.ioworker import io_reader
from nectar import admin
from pprint import pprint
from os.path import join as pathjoin
from os import unlink
import logging
import sys
import copy

import asyncio
import time

def pubkey_reply(handler, args):
        print('running pubkey_reply!')


#TODO use a decorator instead here:
ROUTES = {
          'PubKeyReply': pubkey_reply,
          }

class TimedDict:
    """
    TimeDict returns values for a key with max_time_secs of life.
    Should a key have a life greater than max_times_secs, it is
    deleted and KeyError is returned.
    """
    def __init__(self, max_time_secs=60):
        self.max_time = max_time_secs
        self.data = {}

    def __getitem__(self, key):
        print(self.data)
        timestamp, item = self.data[key]
        if self.now() - timestamp > self.max_time:
            del self.data[key]
            raise KeyError
        else:
            # update timestamp
            self.data[key] = (self.now(), item)
            return item
        

    def __setitem__(self, key, value):
        self.data[key] = (self.now(), value)

                
    def expire(self):
        "removes any old keys"
        to_delete = []
        for k, v in self.data.items():
            if self.now() - v[0] > self.max_time:
                to_delete.append(k)
        for k in to_delete:
            del self.data[k]
            
    def now(self):
        return time.time()
    

class PomaresServer:
    def __init__(self, key_path, address='0.0.0.0', port=8080,
                 admin_sock=admin_sock_file):
        self.address = address
        self.port = port
        self.keyobj = load_key(key_path)
        self.routes = ROUTES

        #PomaresProtocol.route = self.route
        self.loop = asyncio.get_event_loop()
        self.server = self.loop.create_datagram_endpoint(PomaresServerProtocol, 
                                                         local_addr=(address, 
                                                                     port))
        PomaresAdminProtocol.route = admin.route
        self.admin_server = self.loop.create_unix_server(PomaresAdminProtocol, 
                                                         path=admin_sock)
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
        session_admin = self.loop.run_until_complete(self.admin_server)
        logging.debug('serving on {}:{}'.format(self.address, self.port))
        logging.debug('serving admin on {}'.format(session_admin.sockets[0].getsockname()))
        self.loop.run_forever()


def start_server(keyfile, address, port):
    server = PomaresServer(pathjoin(key_path, keyfile), address, port)
    server.run()


if __name__ == '__main__':
    if sys.argv[1] == 'client':
        loop = asyncio.get_event_loop()
        payload = sys.argv[2]
        payload = bytes(payload.encode())
        print('input size: {}'.format(len(payload)))
        payload = compress_buff(payload)
        print('payload size: {}'.format(4+len(payload)))
        server_prot = PomaresProtocol(payload)
        loop.run_until_complete(loop.create_connection(lambda: server_prot,
                                                       host='127.0.0.1',
                                                       port=8080))
        loop.run_forever()
        loop.close()
