"""the metadata store module"""

import nectar.db as db
from nectar.config import db_path, db_path_local, db_path_shared_trees
from nectar.config import db_path_shared_basenames, db_path_remote
from nectar.utils import path_valid, PathNotValidException
import pickle
from os.path import join as pathjoin


class Store():
    def __init__(self, name, path=db_path, prefix_subdir=0,
                 create_new=True, strict_path=True,
                 name_fmt=None):

        # use prefix subdir with value:
        if prefix_subdir:
            path = pathjoin(path, name[:prefix_subdir])
            name = name[prefix_subdir:]

        # verify that name and path are safe/inclusive:
        if strict_path:
            valid, common = path_valid(path, pathjoin(path, name))

            if not valid:
                return PathNotValidException('%s is not valid/allowed'
                                             % (pathjoin(path, name)))

        self.dbname = '%s' % (name, )
        self.db = db.get(self.dbname, path=path, name_fmt=name_fmt)

        # create new dir if create_new is True
        if not self.db and create_new:
            self.db = db.new(self.dbname, path=path, name_fmt=name_fmt)

    def __getitem__(self, key):
        try:
            val = self.db.db[pickle.dumps(key)]
            return pickle.loads(val)
        except KeyError:
            return None

    def __setitem__(self, key, value):
        self.db.db[pickle.dumps(key)] = pickle.dumps(value)

    def __delitem__(self, key):
        del self.db.db[pickle.dumps(key)]

    def __iter__(self):
        k = self.db.db.firstkey()
        while k is not None:
            yield pickle.loads(k)
            k = self.db.db.nextkey(k)

    def __contains__(self, key):
        return pickle.dumps(key) in self.db.db


class SumKey(Store):
    """get/set the key of a keychecksum"""
    def __init__(self, name='sum-key'):
        Store.__init__(self, name, path=db_path_local,
                       name_fmt='key/%s' % (name,))


class SumAlias(Store):
    """get/set the alias of a keychecksum"""
    def __init__(self, name='sum-alias'):
        Store.__init__(self, name, path=db_path_local,
                       name_fmt='alias/%s' % (name,))


class SumManaged(Store):
    """get/set managing of a keychecksum"""
    def __init__(self, name='sum-managed'):
        Store.__init__(self, name, path=db_path_local,
                       name_fmt='managed/%s' % (name,))


class SumPeers(Store):
    """get/set peers for a keychecksum"""
    def __init__(self, name='sum-peers'):
        Store.__init__(self, name, path=db_path_local,
                       name_fmt='peers/%s' % (name,))


class SumAllow(Store):
    """get/set the tree access details for a keychecksum"""
    def __init__(self, name):
        Store.__init__(self, 'allow',
                       path=pathjoin(db_path_shared_trees, name),
                       name_fmt='trees/%s/allow' % (name,))


class SumCapabilities(Store):
    """get/set the capabilities for a keychecksum"""
    def __init__(self, name='sum-capabilities'):
        Store.__init__(self, name, path=db_path_remote,
                       name_fmt='capabilities/%s' % (name,))


class FileState(Store):
    """get/set the written chunks of a file"""
    def __init__(self, name, path):
        Store.__init__(self, ".%s" % (name,), path=path,
                       name_fmt='filestate/%s' % (name,))

    def __getitem__(self, key):
        try:
            val = self.db.db[pickle.dumps(key)]
            return val
        except KeyError:
            return None

    def __setitem__(self, key, value):
        self.db.db[pickle.dumps(key)] = pickle.dumps(value)


class HashBasenames(Store):
    """get/set the basenames and meta for a file hash"""
    def __init__(self, name):
        Store.__init__(self, name, path=db_path_shared_basenames,
                       prefix_subdir=2,
                       name_fmt='basenames/%s' % (name,))


class TreeHashes(Store):
    """get/set the hashes of a tree name"""
    def __init__(self, name):
        Store.__init__(self, 'basenames',
                       path=pathjoin(db_path_shared_trees, name),
                       name_fmt='trees/%s/basenames' % (name,))

if __name__ == '__main__':
    """simple tool to display key-value pairs in Store files"""
    import sys
    import os
    import pprint
    import cPickle
    name = os.path.basename(sys.argv[1])
    dirname = os.path.dirname(sys.argv[1])
    s = db.get(name=name, path=dirname, read_only=True)

    k = s.db.firstkey()
    while k is not None:
        pprint.pprint(dict([(cPickle.loads(k), cPickle.loads(s.db[k]))]))
        k = s.db.nextkey(k)
