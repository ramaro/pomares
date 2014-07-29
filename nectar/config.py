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
chunk_size: 8192
debug_file: %(config_dir)s/debug.log
db_path: %(config_dir)s/db
db_path_local: %(config_dir)s/db/local
db_path_remote: %(config_dir)s/db/remote
db_path_remote_shared: %(config_dir)s/db/remote/shared
db_path_shared_basenames: %(config_dir)s/db/remote/shared/basenames
db_path_shared_trees: %(config_dir)s/db/remote/shared/trees
sock_path: %(config_dir)s/sock

key_path: %(config_dir)s/keys

request_timeout = 60
connect_timeout = 30
"""     % {'config_dir': config_dir})
        conf.close()
    except:
        print("Unable to setup initial configuration file %s" % \
              os.path.expanduser(config_file),
              file=sys.stderr) 
        sys.exit(1)


cp.read(os.path.expanduser(config_file))
chunk_size = cp.getint('Main', 'chunk_size')
request_timeout = cp.getint('Main', 'request_timeout')
connect_timeout = cp.getint('Main', 'connect_timeout')
debug_file = os.path.expanduser(cp.get('Main', 'debug_file'))
db_path = os.path.expanduser(cp.get('Main', 'db_path'))
db_path_local = os.path.expanduser(cp.get('Main', 'db_path_local'))
db_path_remote = os.path.expanduser(cp.get('Main', 'db_path_remote'))
db_path_remote_shared = os.path.expanduser(cp.get('Main',
                                                  'db_path_remote_shared'))
db_path_shared_basenames = os.path.expanduser(cp.get('Main',
                                                     'db_path_shared_basenames'))
db_path_shared_trees = os.path.expanduser(cp.get('Main',
                                                 'db_path_shared_trees'))
sock_path = os.path.expanduser(cp.get('Main', 'sock_path'))
key_path = os.path.expanduser(cp.get('Main', 'key_path'))

create_dir(db_path)
create_dir(db_path_local)
create_dir(db_path_remote)
create_dir(db_path_remote_shared)
create_dir(db_path_shared_trees)
create_dir(db_path_shared_basenames)
create_dir(sock_path)
create_dir(key_path)
