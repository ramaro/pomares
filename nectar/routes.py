from nectar import proto
import logging


def echo(handler, request):
    new_msg = proto.encode(proto.Ack(b'echo ' + request.value))
    new_msg = handler.box.encrypt(new_msg)
    handler.send_data(proto.compress_buff(new_msg))


def talk_client(handler, request):
    pass

# TODO make this a decorator instead
ROUTES_SERVER = {'Ack': echo}


def talk_server(handler, request):
    try:
        req_type = request.__class__.__name__
        func = ROUTES_SERVER[req_type]
        # found route, execute:
        logging.info('(talk_server) routing {} -> {}'.format(req_type, func))
        func(handler, request)
    except KeyError as err:
        logging.info('(talk_server) no route '+err)
