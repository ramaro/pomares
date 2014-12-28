"""cli code"""
from nectar import store
from nectar import server
from nectar import crypto
from nectar import config
from collections import namedtuple
import os.path
from os import listdir, unlink
import logging
import re

def run(args):
    """starts server"""
    try:
        server.start_server(args.keyfile, args.address, args.port,
                            args.admin)
    except KeyboardInterrupt:
        logging.info('got a KeyboardInterrupt, quitting.')
        unlink(args.admin)

def genkeys(args):
    """generates key files"""
    if not args.keyfile:
        crypto.generate_keys(config.key_file)
    else:
        crypto.generate_keys(os.path.join(config.key_path,args.keyfile))

def keypairs(args):
    """Lists keypair files in keypath"""
    for f in listdir(config.key_path):
        print('- {}'.format(f))


def alias(args):
    #TODO add -f to force when it already exists (project wide!)
    aliases = store.SumAlias()
    aliases[args.keysum] = args.name
    print('*', args.name)

def alias_sum(alias):
    """returns key sum of alias"""
    aliases = store.SumAlias()
    for k in aliases:
        if alias == aliases[k]:
            return k

def unalias(args):
    """delete alias"""
    aliases = store.SumAlias()
    for keysum in aliases:
        #delete only first occurrence
        if args.name == aliases[keysum]:
            del aliases[keysum]
            break

def aliases(args):
    """print aliases"""
    aliases = store.SumAlias()
    for k in aliases:
        print("%s\t%s" % (aliases[k], k))

def peers(args):
    """print peers"""
    _peers = store.SumPeers()
    aliases = store.SumAlias()
    for k in _peers:
        if aliases[k]:
            print("%s\t%s" % (aliases[k], _peers[k]))
        else:
            print("%s\t%s" % (k, _peers[k]))


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
                    print(fullpath, _hash)

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

                except IOError as err:
                    print('%s: %s, skipping...' % (fullpath,err.args))
                    pass
    finally:
        chdir(pwd)


def share(args):
    """[local]"""

    # create task_list of filenames and meta:
    task_list = share_dir(args.directory, args.tree)

    # send values to managed peer:
    do_managed(ShareTreeFileRequest, task_list)


def pubkeys(args):
    sumkeys = store.SumKey()
    aliases = store.SumAlias()
    for k in sumkeys:
        if args.alias:
            if aliases[k] in args.alias:
                print("%s %s [%s]" % (aliases[k],),
                                      pubkey_sum(sumkeys[k],
                                                 from_key=True),
                                      pubkey_encode(sumkeys[k], from_key=True))
        else:
            print("%s %s [%s]" % (aliases[k],),
                                  pubkey_sum(sumkeys[k], from_key=True),
                                  pubkey_encode(sumkeys[k], from_key=True))


def pubkey(args):
    """key is in base64 [remote/local]"""

    pubkey = crypto.pubkey_from_base64(args.pubkey)
    #args.address ##optional##
    sumpeers = store.SumPeers()
    managed = managed_session()

    if not managed:
        print('no managed peer set.')
        exit(1)

    managed_peer = sumpeers[managed]

    if not managed_peer:
        # if address is supplied,
        # we want to use this as a managed peer instead [local]
        if args.address:
            managed_peer = args.address
            sumpeers[managed] = managed_peer
        else:
            print('no managed peer address set/found.')
            exit(1)

    #we've got a managed peer here
    if managed and managed_peer:
        #put a SetValuesRequest[remote] in the client's task_queue
        #for the new key with empty capabilities
        #on succcess reply, update aliases [local]
        sv = SetValuesRequest(db='store.SumCapabilities',
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
            sumkeys = store.SumKey()
            sumkeys[alias_args.keysum] = pubkey.encode()
        except BadHandshake:
            print('got a bad handshake, aborting.')
            exit(1)
        except SetValuesRequestError:
            print('couldn\'t set values, aborting.')
            exit(1)


def do_managed(request_type, task_list):
    """send a task_list of values on in currently managed peer
       task_list is a list of parameters for request_type"""

    sumpeers = store.SumPeers()
    sumkeys = store.SumKey()
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
        print('got a bad handshake, aborting.')
        exit(1)
    except SetValuesRequestError:
        print('couldn\'t set values, aborting.')
        exit(1)


def peer(args):
    """
    add peers [local]
    needs an alias to exist first.
    """

    aliases = store.SumAlias()
    sumpeers = store.SumPeers()

    for k in aliases:
        if aliases[k] == args.alias:
            if (not sumpeers[k]) or args.force:
                sumpeers[k] = args.address
                break
            else:
                print('peer for %s already set. (use the --force)' % args.alias)
                exit(1)


def manage(args):
    """
    Set or show managed peers [local]
    """
    summanaged = store.SumManaged()
    sumaliases = store.SumAlias()

    if args.alias:
        #lookup alias:
        for k in sumaliases:
            if args.alias == sumaliases[k]:
                summanaged[k] = 'manage'
                open(pathjoin(config.config_dir, 
                              '.managed_session'), 'w').write(k)
                print('*', args.alias)
                break
    else:
        current_session = managed_session()
        if not current_session:
            print('No current session set')
            exit(1)

        for k in summanaged:
            if k == current_session:
                print('*',)
            print(sumaliases[k])


def managed_session():
    """Returns currently managed session [local]"""
    try:
        current_session = open(pathjoin(config.config_dir, 
                               '.managed_session')).read()
        return current_session
    except IOError:
        return None


def managed_peer():
    """Returns currently managed session peer [local]"""
    current_session = managed_session()
    if current_session:
        return store.SumPeers()[current_session]


def admin(args):
    """set alias or local key as admin [local|remote]"""

    if args.local:
        #alias is the key location in disk instead [local]:
        local_key = crypto.load_key(args.alias)
        alias_args = namedtuple('newargs', ('keysum', 'name'))
        alias_args.keysum = crypto.pubkey_sum(local_key)
        alias_args.name = 'local'
        alias(alias_args)
        sumcapabilities = store.SumCapabilities()
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
                print('alias %s not found.' % args.alias)
                exit(1)

            sv = SetValuesRequest(db='store.SumCapabilities',
                                  values={'key': keysum, 'value': 'admin'})
            host, port = managed_peer().split(':')
            task_queue = Queue()
            task_queue.put(sv)
            try:
                #[remote]
                sumkey = store.SumKey()
                server_pubkey = sumkey[current_session]
                if server_pubkey is None:
                    print('alias key not found.')
                    exit(1)
                server_pubkey = pubkey_from_key(server_pubkey)
                if not server_pubkey:
                    print('can\'t find managed session key.')
                    exit(1)
                PomaresClientHandler((host, port),
                                     pub_key, priv_key,
                                     server_pubkey, task_queue)

            except BadHandshake:
                print('got a bad handshake, aborting.')
                exit(1)
            except SetValuesRequestError:
                print('couldn\'t set values, aborting.')
                exit(1)


def allow(args):
    """set tree access details [remote]"""

    if re.match('[rw]+|0|none', args.perm):
        keysum = alias_sum(args.alias)
        if keysum:
            task = (args.tree, keysum, args.perm)
            do_managed(SetPermsRequest, [task])
        else:
            print('alias %s not found.' % args.alias)
            exit(1)
    else:
        print('wrong perms.')
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
