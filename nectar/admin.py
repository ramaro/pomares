"admin server-side commands"
import logging

def route(self, handler, msg):
    logging.debug('(admin route) I am routing this cmd: {}'.format(msg))
    if msg.decode() == 'ping':
        logging.debug('sending: pong')
        handler.send_data('pong')
