#!/usr/bin/env python3.4
import argparse
import sys

from nectar import server, cli, utils, config, crypto


def startserver():
    server.start_server()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Pomares file distribution.')
    subparsers = parser.add_subparsers(help='commands')

    start_parser = subparsers.add_parser('run', help='Run server')
    start_parser.add_argument('--address',
                              action='store',
                              help='Address to listen on (default is 0.0.0.0)',
                              default='0.0.0.0', type=str, nargs='?')
    start_parser.add_argument('--port',
                              action='store',
                              help='Port to listen to (default is 8080)',
                              default=8080, type=int, nargs='?')
    start_parser.add_argument('--keyfile',
                              action='store',
                              help='Keypair file to use (default is my.key)',
                              default='my.key', type=str, nargs='?')
    start_parser.add_argument('--admin',
                              action='store',
                              help='Admin sock file to use (default is admin.sock)',
                              default='admin.sock', type=str, nargs='?')


    list_parser = subparsers.add_parser('ls', help='List contents')


    list_parser = subparsers.add_parser('keypairs', help='List keypair files')

    list_parser.add_argument('dirname', action='store',
                             help='Directory to list',
                             default='/', nargs='*')


    genkeys_parser = subparsers.add_parser('genkeys', help='Generate keypair files')
    genkeys_parser.add_argument('keyfile', action='store', help='keypair filename',
                                default=None, nargs='?')

    about_parser = subparsers.add_parser('about',
                                         help='About this instance')

    share_parser = subparsers.add_parser('share', help='Share directory')
    share_parser.add_argument('tree', action='store', help='Tree name')
    share_parser.add_argument('directory', action='store',
                              help='Directory path')

    shared_parser = subparsers.add_parser('shared', help='List shared trees')

    # aka, connect/join tree
    tree_parser = subparsers.add_parser('tree', help='Add remote tree')
    tree_parser.add_argument('alias', action='store', help='Peer Alias')
    tree_parser.add_argument('tree', action='store', help='Tree name')


    key_parser = subparsers.add_parser('pubkey', help='Add public key')
    key_parser.add_argument('alias', action='store', help='Alias')
    key_parser.add_argument('pubkey', action='store', help='Public Key')
    key_parser.add_argument('address', action='store',
                            default=None, nargs='?',
                            help='Set address to key (add new peer)')


    args = parser.parse_args()

    try:
        func = getattr(cli, sys.argv[1])
        func(args)
    except IndexError:
        parser.print_help()

