from config import pub_key, priv_key
from nacl.public import PrivateKey, PublicKey
from nacl.hash import sha256
from nacl.encoding import Base64Encoder
from gevent.socket import wait_write
from sendfile import sendfile as pysendfile
from errno import EAGAIN, EBUSY
from os import chmod
from os.path import abspath, commonprefix, relpath
from os.path import exists as pathexists


def gevent_sendfile(out_fd, in_fd, offset, count):
    total_sent = 0
    while total_sent < count:
        try:
            sent = pysendfile(out_fd, in_fd,
                              offset + total_sent,
                              count - total_sent)

            #print '%s: sent %s [%d%%]' % (out_fd, sent, 100*total_sent/count)
            total_sent += sent
        except OSError, err:
            #print 'OSError'
            if err.errno in (EAGAIN, EBUSY):
                wait_write(out_fd)
            else:
                raise

    return offset + total_sent, total_sent


def patch_sendfile():
    import sendfile
    sendfile.sendfile = gevent_sendfile


patch_sendfile()


def path_valid(local_path, requested_path):
    """checks if requested_path is included in local_path
    returns comparison and common path"""

    common = commonprefix((abspath(requested_path), local_path))

    return relpath(common, local_path) == '.', common


class PathNotValidException(Exception):
    pass


def load_key(path, key_type=None):
    """returns a PublicKey, PrivateKey object or just a key string
       from a file in path"""
    key = open(path).read()

    if key_type == 'pub':
        return PublicKey(key)

    if key_type == 'priv':
        return PrivateKey(key)

    return key


def pubkey_sum(pubkey, from_key=False):
    """returns a sha256 keysum for a pubkey object
    use from_key to read from key string"""

    if from_key:
        return sha256(PublicKey(pubkey).encode())

    return sha256(pubkey.encode())


def pubkey_encode(pubkey, from_key=False):
    """returns a base64 enconded string for pubkey
    use from_key to read from a key string"""

    if from_key:
        return PublicKey(pubkey).encode(encoder=Base64Encoder)
    return pubkey.encode(encoder=Base64Encoder)


def pubkey_from_b64(pub_b64):
    """returns a PublicKey object from pub_b64, a base64 enconded string"""
    return PublicKey(pub_b64, encoder=Base64Encoder)


def pubkey_from_key(key):
    """returns a PublicKey object for string key"""

    return PublicKey(key)


def generate_keys(force=False):
    """generates key pairs in pomares home dir"""
    if not force:
        if pathexists(pub_key) or pathexists(priv_key):
            raise Exception("key files exist, not overwriting")

    k = open(pub_key, 'w')
    prvk = PrivateKey.generate()
    k.write(prvk.public_key._public_key)
    k.close()
    k = open(priv_key, 'w')
    k.write(prvk._private_key)
    k.close()
    chmod(pub_key, 0400)
    chmod(priv_key, 0400)
