#!/usr/bin/env python3.4
import argparse
import sys
from nectar import server, cli


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
                              help='Keypair file to use (default is local.key)',
                              default='local.key', type=str, nargs='?')

    list_parser = subparsers.add_parser('ls', help='List pomares or trees')
    list_parser.add_argument('--exported',
                             action='store_true',
                             default=False,
                             help='List exported trees')
    list_parser.add_argument('--imported',
                             action='store_true',
                             default=True,
                             help='List imported trees (default)')

    keypairs_parser = subparsers.add_parser('keypairs',
                                            help='List keypair files')

    keypairs_parser.add_argument('dirname', action='store',
                                 help='Directory to list',
                                 default='/', nargs='*')

    genkey_parser = subparsers.add_parser('genkey',
                                          help='Generate keypair files')
    genkey_parser.add_argument('keyfile', action='store',
                               help='keypair filename',
                               default=None, nargs='?')

    key_parser = subparsers.add_parser('pubkey', help='Add public key')
    key_parser.add_argument('alias', action='store', help='Alias')
    key_parser.add_argument('pubkey', action='store', help='Public Key')
    key_parser.add_argument('address', action='store',
                            help='Set address to key (add new peer)')

    export_parser = subparsers.add_parser('export', help='Export local tree')
    export_parser.add_argument('directory', action='store',
                               help='Directory path')
    export_parser.add_argument('tree', action='store', help='Tree name')

    # aka, connect/join tree
    import_parser = subparsers.add_parser('import', help='Import remote tree')
    import_parser.add_argument('alias', action='store', help='Peer Alias')
    import_parser.add_argument('tree', action='store', help='Tree name')

    raw_parser = subparsers.add_parser('raw',
                                       help='Send raw commands to admin sock')
    raw_parser.add_argument('command', action='store',
                            help='raw command')

    about_parser = subparsers.add_parser('about',
                                         help='About this instance')

    args = parser.parse_args()

    try:
        # TODO get rid of this when using click
        # instead of argparse
        if sys.argv[1] == 'import':
            func = cli.import_tree
        else:
            func = getattr(cli, sys.argv[1])
        func(args)
    except IndexError:
        parser.print_help()
