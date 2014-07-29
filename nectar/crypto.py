"""crypto basic functions"""
from libnacl.public import SecretKey, Box, PublicKey
from libnacl.secret import SecretBox
from libnacl.utils import load_key as j_loadkey
from hashlib import sha256

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


def generate_keys(key_path):
    """generate keys in key_path"""
    sk = SecretKey()
    sk.save(key_path)

def load_key(key_path):
    """returns a SecretKey obj for key_path"""
    return j_loadkey(key_path)

def pubkey_sum(keyobj):
    """returns a sha256 keysum for public key in keyobj"""

    h = sha256()
    h.update(keyobj.pk)

    return h.hexdigest()
