"admin server-side commands"
from nectar.utils import logger
from nectar import index
from json import dumps, loads
from cerberus import Validator, ValidationError


class BadJsonMessage(Exception):
    pass


class BadRequest(Exception):
    pass


class BadSchema(Exception):
    pass

validator = Validator()


def index_add(handler, values, index_name='seeded'):
    logger.debug('index add_msg {}'.format(values))
    # check in the handler already has an index_writer
    if handler.index_writer:
        handler.index_writer.add_document(**values)
    else:
        handler.index_writer = index.get_writer(index_name)
        handler.index_writer.add_document(**values)


def seed_msg(*args):
    index_add(*args)


seed_msg_schema = {'checksum': {'type': 'string',
                                'minlength': 64,
                                'maxlength': 64,
                                'required': True},
                   'tree_path': {'type': 'string',
                                 'required': True},
                   'tree': {'type': 'string',
                            'required': True},
                   'path': {'type': 'string',
                            'required': True},
                   'size': {'type': 'number'},
                   'mtime': {'type': 'number'},
                   }


def plant_msg(*args):
    index_add(*args, index='planted')


def ping_msg(handler, values):
    return dumps(['pong'])


def route(self, handler, msg):
    logger.debug('routing: {}'.format(msg))
    try:
        msg = loads(msg.decode())
    except ValueError:
        # Any ValueError means a bad json message
        logger.debug('raising BadJsonMessage')
        handler.send_data('["bad_json"]')
        raise BadJsonMessage()

    admin_commands = {'ping': (ping_msg, {}),
                      'seed': (seed_msg, seed_msg_schema),
                      'planted': (plant_msg, {})
                      }
    try:
        # split header from values
        # default cmd_values is {}
        try:
            cmd_header = msg[0]
            cmd_values = msg[1]
        except IndexError:
            cmd_values = {}  # default

        # grab func, schema and validate
        func, schema = admin_commands[cmd_header]
        try:
            if not validator.validate(cmd_values, schema):
                logger.info('msg not valid')
                raise BadSchema()
        except ValidationError:
                logger.info('validation error')
                raise BadSchema()

        # run func
        cmd_reply = func(handler, cmd_values)
        if cmd_reply:
            logger.debug('sending: {}'.format(cmd_reply))
            handler.send_data(cmd_reply)
        else:
            # Ack if cmd_reply is empty
            logger.debug('sending: {}'.format(dumps(['ack'])))
            handler.send_data(dumps(['ack']))
    except KeyError:
        # Any KeyError means a bad request
        handler.send_data(dumps(['bad_request']))
    except BadSchema:
        # Any KeyError means a bad request
        handler.send_data(dumps(['bad_schema']))
    except BadJsonMessage:
        # Any KeyError means a bad request
        handler.send_data(dumps(['bad_json']))
