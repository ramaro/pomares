"""command line interface"""
from nectar import server
from nectar import crypto
from nectar import config
from nectar import client
from nectar import tree
from nectar.utils import logger
import os
import json


def run(args):
    """starts server"""
    try:
        server.start_server(args.keyfile, args.address, args.port)
    except KeyboardInterrupt:
        logger.info('got a KeyboardInterrupt, quitting.')
        os.unlink(config.admin_sock_file)


def genkey(args):
    """generates key files"""
    if not args.keyfile:
        crypto.generate_keys(config.key_file)
    else:
        crypto.generate_keys(os.path.join(config.key_path,
                                          args.keyfile))


def keypairs(args):
    """Lists keypair files in keypath"""
    for f in os.listdir(config.key_path):
        keyobj_path = os.path.join(config.key_path, f)
        keyobj = crypto.load_key(keyobj_path)
        print('{}: {}'.format(f, crypto.pubkey_base64(keyobj)))


def pubkey(args):
    "Saves a pubkey for an alias"
    pubkey_path = os.path.join(config.pubkey_path, args.alias)
    pubkey_path += '.pubkey'
    if os.path.exists(pubkey_path):
        print("pubkey for alias {} already exists.".format(args.alias))
        return
    with open(pubkey_path, 'w') as f:
        f.write(json.dumps({'pub': args.pubkey}))


def about(args):

    keyobj = crypto.load_key(config.key_file)
    print('key_file:', config.key_file)
    print('public_key:', crypto.pubkey_base64(keyobj))
    print('public_sum:', crypto.pubkey_sum(keyobj))


def export(args):
    """export directory as tree."""
    tree.export_dir(args.directory, args.tree)


def do_admin(cmd_header, cmd_values_list):
    """send a command list to an admin socket"""
    admin_client = client.PomaresAdminClient
    commands = ((json.dumps((cmd_header, c)) for c in cmd_values_list))
    admin_client(config.admin_sock_file, commands).run()


def raw(args):
    """send a raw json command to an admin socket"""
    admin_client = client.PomaresAdminClient
    commands = [args.command]
    admin_client(config.admin_sock_file, commands).run()


def import_tree(args):
    """import (remote) tree"""
    args.tree
    args.alias

    pass


def ls(args):
    """list trees"""
    if args.exported:
        tree_path = os.path.join(config.tree_path, 'exports')
        # display directories only
        for tree_name in os.listdir(tree_path):
            tree_name_path = os.path.join(tree_path, tree_name)
            if(os.path.isdir(tree_name_path)):
                print("{}".format(tree_name[:len(tree_path)]))


def get(args):
    """get file [remote]"""
    args.hash
    args.dirname
    args.stdout

    tree, hash = args.hash.split('/')
