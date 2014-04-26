import argparse
import sys
from docopt import docopt

from nectar import server, cli, utils


def startserver():
    server.start_server()

if __name__ == '__main__':
    doc = """Pomares.

    Usage:
      pomares start [--port=<port>]
      pomares stop
      pomares list [DIRNAME [DIRNAME...]]
      pomares get hash [--stdout] <hash> [DIRNAME]
      pomares get admin
      pomares set admin <alias>
      pomares set admin (-l|--local) <key_path> [ALIAS]
      pomares unset admin <alias>
      pomares get managed
      pomares set managed <alias>
      pomares get alias [ALIAS]
      pomares set alias <name> <keysum>
      pomares unset alias <name>
      pomares get key [ALIAS]
      pomares set key <key> <alias> [ADDRESS]
      pomares unset key <key> <alias>
      pomares get peer [ALIAS]
      pomares set peer <alias> <address>
      pomares unset peer <alias>
      pomares get shared [TREE_NAME]
      pomares set shared <tree_name> <dir>
      pomares unset shared <tree_name> [DIR]
      pomares get tree [TREE_NAME]
      pomares set tree <alias> <tree_name>
      pomares get perms <alias> 
      pomares set perms <alias> <tree_name> (r|w|rw|none)
      pomares get pomar [NAME] 
      pomares set pomar <name> <alias:tree>...
      pomares genkeys [--force]
      pomares about

    Options:
      -h --help     Show this screen.
      --version     Show version.

    """ 

    opts = docopt(doc)
    print opts
    print filter(lambda k: opts[k],  opts.keys())
    print filter(lambda v: v,  opts.values())

    sys.exit(1)


    parser = argparse.ArgumentParser(description='Pomares file distribution.')
    subparsers = parser.add_subparsers(help='Command')

    start_parser = subparsers.add_parser('start', help='Start server')
    start_parser.add_argument('port',
                              action='store',
                              help='Port to listen to (default is 8080)',
                              default=8080, type=int, nargs='?')

    stop_parser = subparsers.add_parser('stop', help='Stop server')

    list_parser = subparsers.add_parser('list', help='List contents')
    list_parser.add_argument('dirname', action='store',
                             help='Directory to list',
                             default='/', nargs='*')

    get_parser = subparsers.add_parser('get', help='Get hash')
    get_parser.add_argument('hash', action='store', help='Hash to get')
    get_parser.add_argument('dirname', action='store',
                            help='Directory to save file to (default is .)',
                            default='.', nargs='?')
    get_parser.add_argument('--stdout', '-', default=False,
                            action='store_true', help='Write file to stdout')

    admin_parser = subparsers.add_parser('admin', help='Set Admins')
    admin_parser.add_argument('-l', '--local', default=False,
                              action='store_true',
                              help='Add local key instead')
    admin_parser.add_argument('alias', action='store', help='Alias Name')

    allow_parser = subparsers.add_parser('allow', help='Allow peer')
    allow_parser.add_argument('alias', action='store', help='Alias Name')
    allow_parser.add_argument('tree', action='store', help='Tree Name')
    allow_parser.add_argument('perm', action='store', help='Permissions',
                              default='r',
                              choices=('r', 'w', 'rw',
                                       'none', '0'), nargs='?')

    allowed_parser = subparsers.add_parser('allowed',
                                           help='List allowed peers')
    # tempnote:can be used to rename aliases
    alias_parser = subparsers.add_parser('alias', help='Alias peer')
    alias_parser.add_argument('name', action='store', help='Alias name')
    alias_parser.add_argument('keysum', action='store', help='Key checksum')

    unalias_parser = subparsers.add_parser('unalias',
                                           help='Unalias peer')
    unalias_parser.add_argument('name', action='store',
                                help='Alias name')

    aliases_parser = subparsers.add_parser('aliases',
                                           help='List aliases')
    genkeys_parser = subparsers.add_parser('genkeys',
                                           help='Generate key pairs')
    about_parser = subparsers.add_parser('about',
                                         help='About this instance')

    share_parser = subparsers.add_parser('share', help='Share directory')
    share_parser.add_argument('tree', action='store', help='Tree name')
    share_parser.add_argument('directory', action='store',
                              help='Directory path')

    # aka, connect/join tree
    tree_parser = subparsers.add_parser('tree', help='Add remote tree')
    tree_parser.add_argument('alias', action='store', help='Peer Alias')
    tree_parser.add_argument('tree', action='store', help='Tree name')


    observe_parser = subparsers.add_parser('observe', help='Observe directory')
    observe_parser.add_argument('tree', action='store', help='Tree name')
    observe_parser.add_argument('directory', action='store',
                              help='Directory path')


    shared_parser = subparsers.add_parser('shared', help='List shared trees')

    manage_parser = subparsers.add_parser('manage',
                                          help='Set or show managed peer')
    manage_parser.add_argument('alias', action='store',
                               help='Set alias as managed peer',
                               default=None, nargs='?')

    seen_parser = subparsers.add_parser('peers', help='List peers')

    peer_parser = subparsers.add_parser('peer', help='Add Peer')
    peer_parser.add_argument('alias', action='store', help='Alias')
    peer_parser.add_argument('address', action='store',
                             help='Address (host:port)')
    peer_parser.add_argument('-f', '--force', default=False,
                             action='store_true', help='Force update')

    keys_parser = subparsers.add_parser('keys',
                                        help='List public keys for peers')
    keys_parser.add_argument('alias', action='store',
                             help='List keys for peers',
                             default=None, nargs='*')

    key_parser = subparsers.add_parser('key', help='Add key')
    key_parser.add_argument('alias', action='store', help='Alias')
    key_parser.add_argument('key', action='store', help='Key')
    key_parser.add_argument('address', action='store',
                            default=None, nargs='?',
                            help='Set address to key (add new peer)')

    pomar_parser = subparsers.add_parser('pomar', help='Set pomar')
    # tempnote:logical name for joined peer trees
    pomar_parser.add_argument('name', action='store', help='Pomar name')
    # temponote:alias is set in aliases
    pomar_parser.add_argument('alias:tree', action='store',
                              help='Alias:tree', nargs='*')

    show_parser = subparsers.add_parser('show', help='Show pomares')

    args = parser.parse_args()
    #print args
    #print sys.argv[1]

    if sys.argv[1] == 'start':
        startserver()

    elif sys.argv[1] == 'genkeys':
        utils.generate_keys()

    else:
        func = getattr(cli, sys.argv[1])
        func(args)
