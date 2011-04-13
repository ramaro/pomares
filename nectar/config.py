import ConfigParser, os, re, sys, uuid

config_file = '~/.pomares/pomares.cfg'

cp = ConfigParser.ConfigParser()

if not os.path.exists(os.path.expanduser(config_file)): 
	try:
		os.makedirs(os.path.dirname(os.path.expanduser(config_file)))
	except OSError:
		pass

	try:
		conf = open(os.path.expanduser(config_file), "w")
	except:
		print "Unable to setup initial configuration file %s" % \
			os.path.expanduser(config_file)
		sys.exit(1)
	
	conf.write("""[Main]
chunk_size: 8192
download_path: ~/.pomares/fruit/
debug_file: ~/.pomares/debug.log
toc_file: ~/.pomares/toc.db
uuid_file: ~/.pomares/uuid.db
max_connections: 3
my_uuid: %s
hosts: 
filename_encoding = utf-8
openfile_time = 60
server_recv_buffer = 8192
client_recv_buffer = 8192
""" % str(uuid.uuid4()))
	conf.close()

cp.read(os.path.expanduser(config_file))

chunk_size = cp.getint('Main', 'chunk_size')
download_path = os.path.expanduser(cp.get('Main', 'download_path'))
hosts = re.split(', *', cp.get('Main', 'hosts'))
debug_file = os.path.expanduser(cp.get('Main', 'debug_file'))
toc_file = os.path.expanduser(cp.get('Main', 'toc_file'))
uuid_file = os.path.expanduser(cp.get('Main', 'uuid_file'))
my_uuid = cp.get('Main', 'my_uuid')
max_connections = cp.getint('Main', 'max_connections')
filename_encoding = 'utf-8'
openfile_time = cp.getint('Main', 'openfile_time')
server_recv_buffer =cp.getint('Main', 'server_recv_buffer')
client_recv_buffer =cp.getint('Main', 'server_recv_buffer')
