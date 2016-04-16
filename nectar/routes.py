from nectar import proto, config
from nectar.utils import logger
import asyncio


def echo(handler, request):
    new_msg = proto.encode(proto.Ack(b'echo ' + request.value))
    new_msg = handler.box.encrypt(new_msg)
    handler.send_data(proto.compress_buff(new_msg))


ROUTES_CLIENT = {'Ack': echo}


def talk_client(handler, request):
    try:
        req_type = request.__class__.__name__
        func = ROUTES_CLIENT[req_type]
        # found route, execute:
        logger.info('routing {} -> {}'.format(req_type, func))
        func(handler, request)
    except KeyError as err:
        logger.info('no route '+err)


def plant_tree_req(handler, request):
    loop = asyncio.get_event_loop()
    # TODO
    """
    if not handler.io_transport:
        handler.io_transport, _ = \
            loop.create_unix_connection(proto.PomaresIOProtocol,
                                        config.io_sock_file)
    """
    new_msg = proto.encode(proto.Ack(b'plant reply ' + request.tree))
    new_msg = handler.box.encrypt(new_msg)
    handler.send_data(proto.compress_buff(new_msg))


# TODO make this a decorator instead
ROUTES_SERVER = {'Ack': echo,
                 'PlantTreeRequest': plant_tree_req}


def talk_server(handler, request):
    try:
        req_type = request.__class__.__name__
        func = ROUTES_SERVER[req_type]
        # found route, execute:
        logger.info('routing {} -> {}'.format(req_type, func))
        func(handler, request)
    except KeyError as err:
        logger.info('no route '+err)
