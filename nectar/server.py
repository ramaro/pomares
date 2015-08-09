from nectar.crypto import CryptoBox, SecretBox, load_key
from nectar.proto import PomaresProtocol, BadHandshake, PubKeyReply
from nectar.proto import PomaresAdminProtocol
from nectar.proto import decompress_buff, compress_buff, encode, decode
from nectar.config import key_path, admin_sock_file
from nectar import admin
from nectar import routes
from nectar.utils import logger
from os.path import join as pathjoin
import sys

import asyncio


class PomaresServer:
    def __init__(self, key_path, address='0.0.0.0', port=8080,
                 admin_sock=admin_sock_file):
        self.keyobj = load_key(key_path)

        PomaresProtocol.route = self.route
        self.loop = asyncio.get_event_loop()
        self.server = self.loop.create_server(PomaresProtocol, address, port)
        PomaresAdminProtocol.route = admin.route
        self.admin_server = self.loop.create_unix_server(PomaresAdminProtocol,
                                                         path=admin_sock)

    def route(self, handler, msg):
        logger.debug('routing msg: {}'.format(msg))
        try:
            msg = decompress_buff(msg)
            logger.debug('decompressed msg: {}'.format(msg))
            if not handler.handshaked:
                msg = decode(msg)
                logger.debug('decoded msg: {}'.format(msg))
                # at this point we can only expect PubKeyReply
                self.do_handshake(handler, msg)
            else:
                msg = handler.box.decrypt(msg)
                request = decode(msg)
                logger.debug('decrypted and decoded msg: {}'.format(request))

                # TODO treat client requests here
                routes.talk_server(handler, request)

        except Exception as err:
            logger.info('ignoring request [bad key] {}'.format(err))
            raise

    def do_handshake(self, handler, msg):
        logger.debug('do_handshake()')
        try:
            # receive client pubkey and create my init_box
            handler.init_box = CryptoBox(self.keyobj)
            logger.debug("server init_box pk: {}".format(self.keyobj.pk))
            logger.debug("server init_box sk: {}".format(self.keyobj.sk))

            # init box with client's pubkey
            handler.init_box.box_with(msg.key)

            # create and send secret
            handler.box = SecretBox()
            sk_msg = encode(PubKeyReply(handler.box.sk))
            sk_msg = handler.init_box.encrypt(sk_msg)
            handler.send_data(compress_buff(sk_msg))

            handler.handshaked = True
            logger.info('HANDSHAKED1')
        except:
            raise BadHandshake()

    def run(self):
        session = self.loop.run_until_complete(self.server)
        session_admin = self.loop.run_until_complete(self.admin_server)
        logger.debug('serving on {}'.format(session.sockets[0].getsockname()))
        logger.debug('serving admin on {}'.format(session_admin.sockets[0].
                                                  getsockname()))
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
