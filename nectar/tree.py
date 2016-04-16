"tree and objects manipulation module"
from nectar import config
import os.path
import os
from hashlib import sha256
import struct
import binascii


def hashfile_chunk(filename, chunk_size=262144):
    """
    returns a generator tuple
    with the sha256 digest object,
    data chunk (default 256KB) and offset for filename.
    """
    offset = 0
    with open(filename, 'rb') as f:
        data = True
        while data:
            data = f.read(chunk_size)
            offset += chunk_size
            digest = sha256()
            digest.update(data)
            if data:
                yield digest, data, offset


def walkdir(dir):
    """
    returns a generator with subdirectories as keys
    and files as values
    """

    # root: Current path which is "walked through"
    # subdirs: Files in root of type directory
    # files: Files in root (not in subFolders) of type other than directory
    for root, subdirs, files in os.walk(dir):
        yield (root, files)
        for subdir in subdirs:
            walkdir(os.path.join(dir, subdir))


def write_object(path, obj_sum, obj_data):
    "writes and creates objects in config.object_path"
    # create object subdirectories
    obj_basedir = os.path.join(config.object_path, obj_sum[:2])
    os.makedirs(obj_basedir)
    with open(os.path.join(obj_basedir, obj_sum), 'wb') as f:
        f.write(obj_data)


def write_state(fstate, obj_sum, obj_offset):
    """
    write offset and hash in binary format
    """
    # write 40B per object offset/sum
    offset_hash = struct.pack('<Q{:d}s'.format(len(obj_sum)),
                              obj_offset, obj_sum)
    fstate.write(offset_hash)


def read_state(fstate_path):
    """
    yields a tuple with offset and checksum
    through a state file in fstate_path
    """
    with open(fstate_path, 'rb') as fstate:
        offset_binhash = True
        while offset_binhash:
            offset_binhash = fstate.read(40)  # 8B offset + 32B hash
            if offset_binhash:
                offset, binhash = struct.unpack('<Q32s', offset_binhash)
                yield offset, binascii.hexlify(binhash).decode()


def write_file_objects_trees(fullpath, treename, obj_hashes):
    """
    write file state trees and objects.
    will create tree structure
    where each file is a offset/object_hash map
    """
    tree_basedir = os.path.join(config.tree_path, 'seeds', treename,
                                os.path.dirname(fullpath))
    tree_basedir = os.path.normpath(tree_basedir)
    filename = os.path.basename(fullpath)
    state_path = os.path.join(tree_basedir, filename)

    # make tree dir:
    try:
        os.makedirs(tree_basedir)
    except FileExistsError:
        pass

    # write state file with obj_offset, obj_sum
    # TODO update state, instead of recreate state
    # write object file with obj_data:
    with open(state_path, 'wb') as fstate:
        for obj_hash in obj_hashes:
            obj_digest, obj_data, obj_offset = obj_hash
            write_state(fstate, obj_digest.digest(), obj_offset)
            try:
                write_object(fullpath, obj_digest.hexdigest(), obj_data)
                # print('\t{}'.format(obj_sum))
            except FileExistsError:
                pass


def seed_dir(dirname, treename):
    """
    seed directories in dirname
    and copy chunk objects under treename
    """
    pwd = os.getcwd()
    try:
        os.chdir(dirname)
        for subdir, files in walkdir('.'):
            for f in files:
                fullpath = os.path.join(subdir, f)
                fullpath = os.path.normpath(fullpath)
                print(fullpath)
                try:
                    obj_hashes = hashfile_chunk(fullpath)
                    write_file_objects_trees(fullpath, treename, obj_hashes)
                except IOError as err:
                    print('%s: %s, skipping...' %
                          (fullpath, err.args))
    finally:
        os.chdir(pwd)
