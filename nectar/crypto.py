"""crypto basic functions"""
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256, SHA
from Crypto.Signature import PKCS1_PSS
from Crypto.Cipher import PKCS1_OAEP
from Crypto import Random
from os import chmod

def generate_keys(pub_path, priv_path, mode=0o400, length=1024):
    """generate keys in pub_path, priv_path with length"""
    o = RSA.generate(length)
    pub = o.publickey().exportKey()
    priv = o.exportKey()

    k = open(pub_path, 'w')
    k.write(pub)
    k.close()

    k = open(priv_path, 'w')
    k.write(priv)
    k.close()

    chmod(pub_path, mode) 
    chmod(priv_path, mode) 

def load_key(priv_path):
    """returns a RSAobj for key in priv_path"""
    priv = RSA.importKey(open(priv_path).read())

    return priv

def pubkey_sum(keyobj):
    """returns a sha256 keysum for keyobj"""

    h = SHA256.new()
    h.update(key.publickey().exportKey('DER'))

    return h.hexdigest()

def encrypt(keyobj, data):
    "returns signature and encrypted data"""
    #OAEP to do the necessary padding
    rsakey = PKCS1_OAEP.new(keyobj)
    enc_data = rsakey.encrypt(data)

    #digest
    h = SHA.new()
    h.update(enc_data)
    signer = PKCS1_PSS.new(keyobj)
    signature = signer.sign(h)

    return signature, enc_data


def decrypt(keyobj, signature, data):
    "returns signed and decrypted data"""
    signer = PKCS1_PSS.new(keyobj)
    rsakey = PKCS1_OAEP.new(keyobj) # for unpadding
    h = SHA.new()
    h.update(data)

    v = signer.verify(h, signature), 
    if v:
        return v, rsakey.decrypt(data)

    return v, None
