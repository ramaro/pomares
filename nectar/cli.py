"""command line interface"""
from nectar import server
from nectar import crypto
from nectar import config
from nectar import client
from collections import namedtuple
from os.path import join as pathjoin
from os import listdir, unlink, getcwd, chdir, walk, stat
from hashlib import sha256
import logging
import re
from json import dumps

def run(args):
    """starts server"""
    try:
        server.start_server(args.keyfile, args.address, args.port)
    except KeyboardInterrupt:
        logging.info('got a KeyboardInterrupt, quitting.')
        unlink(config.admin_sock_file)

def genkey(args):
    """generates key files"""
    if not args.keyfile:
        crypto.generate_keys(config.key_file)
    else:
        crypto.generate_keys(pathjoin(config.key_path,args.keyfile))

def keypairs(args):
    """Lists keypair files in keypath"""
    for f in listdir(config.key_path):
        print('- {}'.format(f))



def about(args):

    keyobj = crypto.load_key(config.key_file)
    print('- public_key', crypto.pubkey_base64(keyobj))
    print('- public_sum', crypto.pubkey_sum(keyobj))
    print()


def walkdir(dir):
    """returns a dict with subdirectories as keys and files as values"""

    #root: Current path which is "walked through"
    #subdirs: Files in root of type directory
    #files: Files in root (not in subFolders) of type other than directory

    for root, subdirs, files in walk(dir):
        yield (root, files)
        for subdir in subdirs:
            walkdir(pathjoin(dir, subdir))

def _hashfile(filename):
    """returns the sha256 hexed digest for filename."""
    m = sha256()
    with open(filename, 'rb') as f:
        data = True
        while data:
            data = f.read(8192)
            m.update(data)

    return m.hexdigest()


def export_dir(dirname, treename):
    pwd = getcwd()
    try:
        chdir(dirname)
        for subdir, files in walkdir('.'):
            for f in files:
                fullpath = pathjoin(subdir, f)
                try:
                    checksum = _hashfile(fullpath)
                    print(fullpath, checksum)

                    _s = stat(fullpath)
                    hb = {'mtime': _s.st_mtime,
                          'size': _s.st_size,
                          'checksum': checksum,
                          'path': fullpath,
                          'tree': treename,
                          'tree_path': dirname}

                    yield (hb)

                except IOError as err:
                    print('%s: %s, skipping...' % (fullpath,err.args))
                    pass
    finally:
        chdir(pwd)


def export(args):
    """export directory."""
    # create task_list of filenames and meta:
    task_list = export_dir(args.directory, args.tree)
    do_admin('export', task_list)


def do_admin(cmd_header, cmd_values_list):
    """send a command list to an admin socket"""
    admin_client = client.PomaresAdminClient
    commands = ((dumps((cmd_header, c)) for c in cmd_values_list))
    admin_client(config.admin_sock_file, commands).run()

def raw(args):
    """send a raw json command to an admin socket"""
    admin_client = client.PomaresAdminClient
    commands = [args.command]
    admin_client(config.admin_sock_file, commands).run()




def tree(args):
    """add remote tree"""
    args.tree
    args.alias

    pass

def get(args):
    """get file [remote]"""
    args.hash
    args.dirname
    args.stdout

    tree, hash = args.hash.split('/')
