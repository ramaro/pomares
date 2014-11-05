"""crypto basic functions"""
from libnacl.public import SecretKey, Box, PublicKey
from libnacl.secret import SecretBox
from libnacl.utils import load_key as j_loadkey
from hashlib import sha256
from base64 import b64encode

class CryptoBox():
    def __init__(self, keyobj):
        self.keyobj = keyobj
        self.box = None

    def box_with(self, peer_pk):
        #create a box with peer_pk (in pk bin format)
        self.box = Box(self.keyobj.sk, peer_pk)

    def encrypt(self, msg):
        return self.box.encrypt(msg)
        
    def decrypt(self, msg):
        return self.box.decrypt(msg)


def generate_keys(key_file):
    """generate keys in key_file"""
    sk = SecretKey()
    sk.save(key_file)

def load_key(key_file):
    """returns a SecretKey obj for key_path"""
    return j_loadkey(key_file)

def pubkey_base64(keyobj):
    """returns the public key in keyobj
    as a base64 string"""

    return b64encode(keyobj.pk).decode() # bytes to utf-8

def pubkey_sum(keyobj):
    """returns a sha256 keysum for public key in keyobj"""

    h = sha256()
    h.update(keyobj.pk)

    return h.hexdigest()
