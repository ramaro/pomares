"""cli code"""
from store import SumAlias, SumManaged, SumCapabilities, SumPeers, SumKey
from utils import pubkey_sum, pubkey_encode, pubkey_from_b64, pubkey_from_key
from config import pub_key, priv_key, config_dir
from utils import load_key
from os.path import join as pathjoin
from os import walk, curdir, chdir, strerror, stat
from client import PomaresClientHandler
from collections import namedtuple
from gevent.queue import Queue
from serialize import SetValuesRequest, SetValuesRequestError
from serialize import ShareTreeFileRequest, SetPermsRequest
from handler import BadHandshake
from sys import exit
from hashlib import sha1
import re


def alias(args):
    #TODO add -f to force when it already exists (project wide!)
    aliases = SumAlias()
    aliases[args.keysum] = args.name
    print '*', args.name


def alias_sum(alias):
    """returns key sum of alias"""
    aliases = SumAlias()
    for k in aliases:
        if alias == aliases[k]:
            return k


def unalias(args):
    aliases = SumAlias()
    for keysum in aliases:
        #delete only first occurrence
        if args.name == aliases[keysum]:
            del aliases[keysum]
            break


def aliases(args):
    aliases = SumAlias()
    for k in aliases:
        print "%s\t%s" % (aliases[k], k)


def peers(args):
    _peers = SumPeers()
    aliases = SumAlias()
    for k in _peers:
        if aliases[k]:
            print "%s\t%s" % (aliases[k], _peers[k])
        else:
            print "%s\t%s" % (k, _peers[k])


def about(args):

    print '[public key]', pubkey_encode(load_key(pub_key, 'pub'))
    print '[public sum]', pubkey_sum(load_key(pub_key, 'pub'))
    print


def walkdir(dir):
    """returns a dict with subdirectories as keys and files as values"""

    #root: Current path which is "walked through"
    #subdirs: Files in root of type directory
    #files: Files in root (not in subFolders) of type other than directory

    dir_structure = {}
    for root, subdirs, files in walk(dir):
        dir_structure[root] = files
        for subdir in subdirs:
            walkdir(pathjoin(dir, subdir))

    return dir_structure


def hashfile(filename):
    """returns the sha1 hexed digest for filename."""
    m = sha1()
    with open(filename, 'r') as f:
        data = True
        while data:
            data = f.read(8192)
            m.update(data)

    return m.hexdigest()


def share_dir(dirname, treename):
    pwd = curdir
    try:
        chdir(dirname)
        for subdir, files in walkdir('.').items():
            for f in files:
                fullpath = pathjoin(subdir, f)
                try:
                    _hash = hashfile(fullpath)
                    print fullpath, _hash

                    _s = stat(fullpath)
                    hb = {'stat': {'ctime': _s.st_ctime,
                                   'atime': _s.st_atime,
                                   'mtime': _s.st_mtime,
                                   'size': _s.st_size,
                                   'mode': _s.st_mode,
                                   'uid': _s.st_uid,
                                   'gid': _s.st_gid},
                          'hash': _hash,
                          'path': fullpath,
                          'tree_path': dirname}

                    yield (treename, {f: hb})

                except IOError, err:
                    print '%s: %s, skipping...' % (fullpath,
                                                   strerror(err.errno))
                    pass
    finally:
        chdir(pwd)


def share(args):
    """[local]"""

    # create task_list of filenames and meta:
    task_list = share_dir(args.directory, args.tree)

    # send values to managed peer:
    do_managed(ShareTreeFileRequest, task_list)


def keys(args):
    sumkeys = SumKey()
    aliases = SumAlias()
    for k in sumkeys:
        if args.alias:
            if aliases[k] in args.alias:
                print "%s %s [%s]" % (aliases[k],
                                      pubkey_sum(sumkeys[k],
                                                 from_key=True),
                                      pubkey_encode(sumkeys[k], from_key=True))
        else:
            print "%s %s [%s]" % (aliases[k],
                                  pubkey_sum(sumkeys[k], from_key=True),
                                  pubkey_encode(sumkeys[k], from_key=True))


def key(args):
    """key is in base64 [remote/local]"""

    pubkey = pubkey_from_b64(args.key)
    #args.address ##optional##
    sumpeers = SumPeers()
    managed = managed_session()

    if not managed:
        print 'no managed peer set.'
        exit(1)

    managed_peer = sumpeers[managed]

    if not managed_peer:
        # if address is supplied,
        # we want to use this as a managed peer instead [local]
        if args.address:
            managed_peer = args.address
            sumpeers[managed] = managed_peer
        else:
            print 'no managed peer address set/found.'
            exit(1)

    #we've got a managed peer here
    if managed and managed_peer:
        #put a SetValuesRequest[remote] in the client's task_queue
        #for the new key with empty capabilities
        #on succcess reply, update aliases [local]
        sv = SetValuesRequest(db='SumCapabilities',
                              values={'key': pubkey_sum(pubkey), 'value': ''})
        host, port = managed_peer.split(':')
        task_queue = Queue()
        task_queue.put(sv)
        try:
            #[remote]
            PomaresClientHandler((host, port), pub_key,
                                 priv_key, pubkey, task_queue)

            #[local]
            alias_args = namedtuple('newargs', ('keysum', 'name'))
            alias_args.keysum = pubkey_sum(pubkey)
            alias_args.name = args.alias
            alias(alias_args)
            #save key:
            sumkeys = SumKey()
            sumkeys[alias_args.keysum] = pubkey.encode()
        except BadHandshake:
            print 'got a bad handshake, aborting.'
            exit(1)
        except SetValuesRequestError:
            print 'couldn\'t set values, aborting.'
            exit(1)


def do_managed(request_type, task_list):
    """send a task_list of values on in currently managed peer
       task_list is a list of parameters for request_type"""

    sumpeers = SumPeers()
    sumkeys = SumKey()
    managed = managed_session()
    managed_peer = sumpeers[managed]

    if not managed_peer:
        raise Exception('no managed peer address set/found.')

    peer_pubkey = sumkeys[managed]

    task_queue = Queue()
    host, port = managed_peer.split(':')
    for vals in task_list:
        dv = request_type(*vals)
        task_queue.put(dv)
    try:
        PomaresClientHandler((host, port), pub_key,
                             priv_key, pubkey_from_key(peer_pubkey),
                             task_queue)

    except BadHandshake:
        print 'got a bad handshake, aborting.'
        exit(1)
    except SetValuesRequestError:
        print 'couldn\'t set values, aborting.'
        exit(1)


def peer(args):
    """add peers [local]"""

    aliases = SumAlias()
    sumpeers = SumPeers()

    for k in aliases:
        if aliases[k] == args.alias:
            if (not sumpeers[k]) or args.force:
                sumpeers[k] = args.address
                break
            else:
                print 'peer for %s already set. (use the --force)' % args.alias
                exit(1)


def manage(args):
    """
    Set or show managed peers [local]
    """
    summanaged = SumManaged()
    sumaliases = SumAlias()

    if args.alias:
        #lookup alias:
        for k in sumaliases:
            if args.alias == sumaliases[k]:
                summanaged[k] = 'manage'
                open(pathjoin(config_dir, '.managed_session'), 'w').write(k)
                print '*', args.alias
                break
    else:
        current_session = managed_session()
        if not current_session:
            print 'No current session set'
            exit(1)

        for k in summanaged:
            if k == current_session:
                print '*',
            print sumaliases[k]


def managed_session():
    """Returns currently managed session [local]"""
    try:
        current_session = open(pathjoin(config_dir, '.managed_session')).read()
        return current_session
    except IOError:
        return None


def managed_peer():
    """Returns currently managed session peer [local]"""
    current_session = managed_session()
    if current_session:
        return SumPeers()[current_session]


def admin(args):
    """set alias or local key as admin [local|remote]"""

    if args.local:
        #alias is the key location in disk instead [local]:
        local_key = load_key(args.alias, 'pub')
        alias_args = namedtuple('newargs', ('keysum', 'name'))
        alias_args.keysum = pubkey_sum(local_key)
        alias_args.name = 'local'
        alias(alias_args)
        sumcapabilities = SumCapabilities()
        sumcapabilities[alias_args.keysum] = 'admin'
        #TODO get the database to RELOAD here
        #as it can be open by the server process
    else:
        #add it do current session [remote]:
        current_session = managed_session()
        if current_session:
            #connect to managed_session
            #and send a SetValues/Admin with new admin key
            keysum = alias_sum(args.alias)
            if not keysum:
                print 'alias %s not found.' % args.alias
                exit(1)

            sv = SetValuesRequest(db='SumCapabilities',
                                  values={'key': keysum, 'value': 'admin'})
            host, port = managed_peer().split(':')
            task_queue = Queue()
            task_queue.put(sv)
            try:
                #[remote]
                sumkey = SumKey()
                server_pubkey = sumkey[current_session]
                if server_pubkey is None:
                    print 'alias key not found.'
                    exit(1)
                server_pubkey = pubkey_from_key(server_pubkey)
                if not server_pubkey:
                    print 'can\'t find managed session key.'
                    exit(1)
                PomaresClientHandler((host, port),
                                     pub_key, priv_key,
                                     server_pubkey, task_queue)

            except BadHandshake:
                print 'got a bad handshake, aborting.'
                exit(1)
            except SetValuesRequestError:
                print 'couldn\'t set values, aborting.'
                exit(1)


def allow(args):
    """set tree access details [remote]"""

    if re.match('[rw]+|0|none', args.perm):
        keysum = alias_sum(args.alias)
        if keysum:
            task = (args.tree, keysum, args.perm)
            do_managed(SetPermsRequest, [task])
        else:
            print 'alias %s not found.' % args.alias
            exit(1)
    else:
        print 'wrong perms.'
        exit(1)


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
