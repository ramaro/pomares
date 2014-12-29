"deal admin commands"
import logging

def route(self, handler, msg):
    logging.debug('(admin route) I am routing this cmd: {}'.format(msg))
    if msg.decode() == 'cmd1':
        handler.send_data('cmd1 reply')
