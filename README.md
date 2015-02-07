# Pomares

Pomares is a distributed content distribuition system written in python 3 (asyncio) that relies on a closed network of trusted peers.

## Features

* Export local content
* Import remote content
* Set logical imports/exports
* Manage peer aliases and public keys
* Peer-to-peer content


## Dependencies

* Python 3.4+
* libnacl
* whoosh
* cerberus
* msgpack-python

## Installation

    pip3 install msgpack-python cerberus Whoosh libnacl
    git clone https://github.com/ramaro/pomares.git
    alias pomares='python3.4 pomares.py' # optional

## Getting Started

#### Generate keypair
    pomares genkey

#### Display public key and info
    pomares about

#### Run Server
    pomares run 

#### Export a local directory
    pomares export ~/public_stuff public

#### Add a peer (example)
    pomares pubkey friend1 eYgtH9qbZFiiVbeGxuVpSyGv6HTkBHiROx5siwyaK3E= friend1.host.name:8111

#### Import a tree from a peer
    pomares import friend1 his_public_stuff

#### List imported trees
    pomares ls

#### Copy imported content
    pomares cp path/to/remote/content local_dir/


## License

MIT License (see LICENSE)
