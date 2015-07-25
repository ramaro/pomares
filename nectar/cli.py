"""command line interface"""
from nectar import server
from nectar import crypto
from nectar import config
from nectar import client
import os.path
from os import listdir, unlink, getcwd, chdir, walk, stat, makedirs
from hashlib import sha256
import logging
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
        crypto.generate_keys(os.path.join(config.key_path,
                                      args.keyfile))


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

    # root: Current path which is "walked through"
    # subdirs: Files in root of type directory
    # files: Files in root (not in subFolders) of type other than directory

    for root, subdirs, files in walk(dir):
        yield (root, files)
        for subdir in subdirs:
            walkdir(os.path.join(dir, subdir))


def _hashfile(filename):
    """
    returns the sha256 hexed digest for filename.
    """
    m = sha256()
    with open(filename, 'rb') as f:
        data = True
        while data:
            data = f.read(8192)
            m.update(data)

    return m.hexdigest()


def _hashfile_chunk(filename, chunk_size=262144):
    """
    returns a generator for a tuple
    with the sha256 hash, data chunk
    and offset for filename.
    """
    m = sha256()
    offset = 0
    with open(filename, 'rb') as f:
        data = True
        while data:
            data = f.read(chunk_size)
            offset += chunk_size
            m.update(data)
            if data:
                yield m.hexdigest(), data, offset


def export_dir(dirname, treename):
    pwd = getcwd()
    try:
        chdir(dirname)
        for subdir, files in walkdir('.'):
            for f in files:
                fullpath = os.path.join(subdir, f)
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
                    print('%s: %s, skipping...' %
                          (fullpath, err.args))
                    pass
    finally:
        chdir(pwd)


def _write_object(path, obj_sum, obj_data):
    "writes and creates objects in config.object_path"
    obj_basedir = os.path.join(config.object_path, obj_sum[:2])
    makedirs(obj_basedir)
    with open(os.path.join(obj_basedir, obj_sum), 'wb') as f:
        f.write(obj_data)
        print('created %s' % os.path.join(obj_basedir, obj_sum))


def _write_state(fstate, obj_sum, obj_offset):
    """
    create tree for export with state files.
    will create tree structure
    where each file is a offset/object_hash map
    maybe use db for state file?
    state file should have meta info as keys too,
    other than offsets
    """
    fstate.write('{},{}\n'.format(obj_offset, obj_sum).encode())


def write_file_objects_trees(fullpath, treename, obj_hashes):
    "write file state trees and objects"
    tree_basedir = os.path.join(config.tree_path, 'exports', treename,
                                os.path.dirname(fullpath))
    tree_basedir = os.path.normpath(tree_basedir)
    filename = os.path.basename(fullpath)
    state_path = os.path.join(tree_basedir, filename)
    print('will write to', state_path)

    # make tree dir:
    try:
        print('trying to makedirs', tree_basedir)
        makedirs(tree_basedir)
    except FileExistsError:
        pass

    # write state file with obj_offset, obj_sum
    # TODO recreate state for now
    # write object file with obj_data:
    with open(state_path, 'wb') as fstate:
        for obj_hash in obj_hashes:
            obj_sum, obj_data, obj_offset = obj_hash
            _write_state(fstate, obj_sum, obj_offset)
            try:
                _write_object(fullpath, obj_sum, obj_data)
            except FileExistsError:
                pass


def export_local(dirname, treename):
    """export directory and copy chunk objects"""
    # XXX local alternative to export() bypassing admin commands
    # XXX should this put a tree directory structure in exports?
    pwd = getcwd()
    try:
        chdir(dirname)
        for subdir, files in walkdir('.'):
            for f in files:
                fullpath = os.path.join(subdir, f)
                try:
                    obj_hashes = _hashfile_chunk(fullpath)
                    write_file_objects_trees(fullpath, treename, obj_hashes)
                except IOError as err:
                    print('%s: %s, skipping...' %
                          (fullpath, err.args))
    finally:
        chdir(pwd)


# TODO get rid for export/import sent to server via admin
# not needed
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
