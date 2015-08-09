from configparser import ConfigParser
import os
import sys
import errno

config_file = os.path.expanduser('~/.pomares/pomares.cfg')
config_dir = os.path.dirname(config_file)

cp = ConfigParser()


def create_dir(path):
    """creates a dir if it doesnt exist."""
    if not os.path.exists(os.path.expanduser(path)):
        try:
            os.makedirs(os.path.expanduser(path))
        except OSError as err:
            if err.errno == errno.EEXIST:
                pass

create_dir(os.path.dirname(config_file))

if not os.path.exists(config_file):
    try:
        conf = open(config_file, "w")
        conf.write("""\
[Main]
debug_file: %(config_dir)s/debug.log
index_path: %(config_dir)s/indexes
object_path: %(config_dir)s/objects
tree_path: %(config_dir)s/trees
index_path_exported: %(config_dir)s/indexes/exported/
index_path_imported: %(config_dir)s/indexes/imported/
sock_path: %(config_dir)s/sock
admin_sock_file : %(config_dir)s/sock/admin.sock
index_sock_file : %(config_dir)s/sock/index.sock

pubkey_path: %(config_dir)s/pubkeys
key_path: %(config_dir)s/keys
key_file: %(config_dir)s/keys/local.key
""" % {'config_dir': config_dir})
        conf.close()
    except:
        print("Unable to setup initial configuration file %s" %
              os.path.expanduser(config_file),
              file=sys.stderr)
        sys.exit(1)


cp.read(os.path.expanduser(config_file))
debug_file = os.path.expanduser(cp.get('Main', 'debug_file'))
index_path = os.path.expanduser(cp.get('Main', 'index_path'))
object_path = os.path.expanduser(cp.get('Main', 'object_path'))
tree_path = os.path.expanduser(cp.get('Main', 'tree_path'))
sock_path = os.path.expanduser(cp.get('Main', 'sock_path'))
admin_sock_file = os.path.expanduser(cp.get('Main', 'admin_sock_file'))
index_sock_file = os.path.expanduser(cp.get('Main', 'index_sock_file'))
pubkey_path = os.path.expanduser(cp.get('Main', 'pubkey_path'))
key_path = os.path.expanduser(cp.get('Main', 'key_path'))
key_file = os.path.expanduser(cp.get('Main', 'key_file'))

create_dir(index_path)
create_dir(object_path)
create_dir(tree_path)
create_dir(sock_path)
create_dir(key_path)
create_dir(pubkey_path)
