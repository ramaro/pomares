"admin server-side commands"
import logging
from nectar import index
from json import dumps, loads

class BadJsonMessage(Exception):
    pass

class BadRequest(Exception):
    pass


def index_add(handler, values, index_name='exported'):
    # TODO schema validate msg values
    logging.debug('(index add_msg) {}'.format(values))
    # check in the handler already has an index_writer
    if handler.index_writer:
        handler.index_writer.add_document(**values[0])
    else:
        handler.index_writer = index.get_writer(index_name)
        handler.index_writer.add_document(**values[0])

def export_msg(*args):
    index_add(*args)

def import_msg(*args):
    index_add(*args, index='imported')

def ping_msg(handler, values):
    return dumps(['pong'])


def route(self, handler, msg):
    logging.debug('(admin route) routing: {}'.format(msg))
    try:
        msg = loads(msg.decode())
    except ValueError:
        # Any ValueError means a bad json message
        logging.debug('(admin route) raising BadJsonMessage')
        handler.send_data('["bad_json"]')
        raise BadJsonMessage()

    admin_commands = {'ping': ping_msg,
                      'export': export_msg,
                      'import': import_msg,
            }
    try:
        cmd_header = msg[0]
        cmd_values = msg[1:]
        cmd_reply = admin_commands[cmd_header](handler, cmd_values)
        if cmd_reply:
            logging.debug('(admin route) sending: {}'.format(cmd_reply))
            handler.send_data(cmd_reply)
        else:
            # Ack if cmd_reply is empty
            logging.debug('(admin route) sending: {}'.format(dumps(['ack'])))
            handler.send_data(dumps(['ack']))
    except KeyError:
        # Any KeyError means a bad request
        handler.send_data(dumps(['bad_request']))
