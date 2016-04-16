"""command line interface"""
from nectar import server
from nectar import crypto
from nectar import config
from nectar import client
from nectar import tree
from nectar import proto
from nectar.utils import logger
import os
import json


def run(address, port, keyfile):
    """starts server"""
    try:
        server.start_server(keyfile, address, port)
    except KeyboardInterrupt:
        logger.info('got a KeyboardInterrupt, quitting.')
        os.unlink(config.admin_sock_file)
        os.unlink(config.io_sock_file)


def genkey(keyfile):
    """generates key files"""
    if not keyfile:
        crypto.generate_keys(config.key_file)
    else:
        crypto.generate_keys(os.path.join(config.key_path,
                                          keyfile))


def keypairs(dirname):
    """Lists keypair files in keypath"""
    for f in os.listdir(config.key_path):
        keyobj_path = os.path.join(config.key_path, f)
        keyobj = crypto.load_key(keyobj_path)
        print('{}: {}'.format(f, crypto.pubkey_base64(keyobj)))


def pubkey(alias, pubkey, address):
    "Saves a pubkey for an alias"
    pubkey_path = os.path.join(config.pubkey_path, alias)
    pubkey_path += '.pubkey'
    if os.path.exists(pubkey_path):
        print("pubkey for alias {} already exists.".format(alias))
        return
    with open(pubkey_path, 'w') as f:
        f.write(json.dumps({'pub': pubkey,
                            'address': address}))


def about():

    keyobj = crypto.load_key(config.key_file)
    print('key_file:', config.key_file)
    print('public_key:', crypto.pubkey_base64(keyobj))
    print('public_sum:', crypto.pubkey_sum(keyobj))


def seed(directory, tree_name):
    """export directory as tree."""
    tree.export_dir(directory, tree_name)


def do_admin(cmd_header, cmd_values_list):
    """send a command list to an admin socket"""
    admin_client = client.PomaresAdminClient
    commands = ((json.dumps((cmd_header, c)) for c in cmd_values_list))
    admin_client(config.admin_sock_file, commands).run()


def raw(command):
    """send a raw json command to an admin socket"""
    admin_client = client.PomaresAdminClient
    commands = [command]
    admin_client(config.admin_sock_file, commands).run()


def plant(alias, tree):
    """import (remote) tree"""
    pubkey_path = os.path.join(config.pubkey_path, alias)
    srv_pubkey, address = crypto.load_pubkey(pubkey_path+'.pubkey')
    my_key = config.key_file
    c = client.PomaresClient(address, my_key, srv_pubkey.pk,
                             proto.ImportTreeRequest(tree))
    c.run()


def ls(seeded, planted):
    """list trees"""
    if seeded:
        tree_path = os.path.join(config.tree_path, 'exports')
        # display directories only
        for tree_name in os.listdir(tree_path):
            tree_name_path = os.path.join(tree_path, tree_name)
            if(os.path.isdir(tree_name_path)):
                print("{}".format(tree_name[:len(tree_path)]))
