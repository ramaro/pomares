"admin server-side commands"
import logging
from json import dumps, loads

class BadJsonMessage(Exception):
    pass

class BadRequest(Exception):
    pass



def route(self, handler, msg):
    logging.debug('(admin route) routing: {}'.format(msg))
    try:
        msg = loads(msg.decode())
    except ValueError:
        # Any ValueError means a bad json message
        logging.debug('(admin router) raising BadJsonMessage')
        handler.send_data('["bad_json"]')
        raise InvalidAdminMessage()

    admin_commands = {'ping': dumps(['pong']),
            }
    try:
        cmd_header = msg[0]
        cmd_values = msg[1:]
        cmd_reply = admin_commands[cmd_header]
        logging.debug('(admin router) sending: {}'.format(cmd_reply))
        handler.send_data(cmd_reply)
    except KeyError:
        # Any KeyError means a bad request
        handler.send_data(dumps(['bad_request']))

