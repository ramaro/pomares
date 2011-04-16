import sys
import readline
import Queue
import re
import os

import client
import resolver
import toc
import config
import file
import talk

request_queue = Queue.Queue()

def list_files(args):
	"""Print a list of files."""
	print 'list_files', args
	tocs = toc.database

	results = None

	try:
		results = tocs.select("""
		select dirname, filename, size, hash, count(uuid), pomar 
		from toc where pomar=? group by filename having max(listversion) order by dirname
		""", (toc.sanitize_pomar(args[0]),)
		)
	except IndexError:
		results = tocs.select("""select dirname, filename, size, hash, count(uuid), pomar 
				from toc group by filename having max(listversion) order by dirname"""
		)

	for n, entry in enumerate(results):
		print n, entry 

def refresh_list(args):
	print 'refresh', args

def get_files(args):
	print 'get_files', args
	try:
		results = toc.whoHas(args[0])

		value = None
		for res in results:
			value = res
			break
		
		if value == None:
			print 'couldnt find hash %s' % args[0]
			return

		pomares_id, filename, filesize, dirname, pomar = value #TODO: temporarily getting the 1st result
		print 'getting:', pomares_id, filename.encode(config.filename_encoding), filesize, dirname.encode(config.filename_encoding), pomar 

		for n, chunk in enumerate(file.chunk_list(filesize)):
			request_queue.put(client.Request('FILE', {'hash':args[0], 'chunk':n}))

	except IndexError:
		print 'couldnt find hash %s' % args[0]

def clear_toc(args):
	print 'clear_toc', args

	tocs = toc.database

	try:
		tocs.execute("""
		delete from toc where uuid=?
		""", (args[0],)
		)
	
	except IndexError:
		answer = raw_input('clear everything? ')

		if 'y' in answer.lstrip().lower(): 
			tocs.execute("""
			delete from toc
			"""
			)

def forget_peer(args):
	resolv = resolver.database

	try:
		resolv.execute("""
		delete from uuid where id=?
		""", (args[0],)
		)
	
	except IndexError:
		answer = raw_input('forget everybody? ')

		if 'y' in answer.lstrip().lower(): 
			resolv.execute("""
			delete from uuid
			"""
			)

def who(args):
	resolv = resolver.database

	try:
		print resolver.resolve(args[0])
	
	except IndexError:
		results = resolv.select("""
		select * from uuid 
		"""
		)

		for w in results:
			print w
		
def info(args):
	print 'My pomares ID:', config.my_uuid
	print 'Request queue size:', request_queue.qsize()
	print 'Client open files:', client.file_objs
	print 'Server open files:', talk.open_files


def status(args):
	print 'status', args

def byebye(args):
	print 'byebye', args
	sys.exit()

def share_pomar(args):
	"""Creates a new pomar and adds files from a pathname"""
	print 'share_pomar', args
	try:
		print 'this might take a while depeding on your cpu and file sizes...'
		add_dir(args[1], args[0])
		toc.updatePomarPath(args[0], args[1])
	except IndexError:
		print 'invalid option\nusage: share pomar path'


def show_help(args):
	print 'show_help', args
	print allow_cmds.keys()

def join_pomar(args):
	print 'join_pomar()', args
	request_queue.put(client.Request('LIST', {} ,internal={'url':args[0]}))

def alias(args):
	print 'alias', args

def get(args):
	print 'get', args

def debug(args):
	print 'debug()', args
	try:
		for r in range(int(args[2])):
			request_queue.put(client.Request(args[0], request_args(args[1]), internal={'url':args[1], 'debug':r}))

	except IndexError:
			request_queue.put(client.Request(args[0], request_args(args[1]), internal={'url':args[1], 'debug':0}))


def add_dir(path, pomar='/'):
	"""Adds contents of directory path to the toc."""

	last_list_version = toc.lastVersionFor(config.my_uuid, pomar)
	if last_list_version is None:
		last_list_version=0

	files = file.list(path)
	new_list_version = last_list_version+1

	for f in files:
		toc.update({'filename':os.path.basename(files[f][0]).decode(config.filename_encoding),
			'size':files[f][1],
			'hash':f,
			'uuid':config.my_uuid,
			'dirname':os.path.dirname(files[f][0]).decode(config.filename_encoding),
			'listversion':new_list_version
			},
		pomar)


def request_args(url):
	"""Returns a dict with arguments given a request url"""
	m = re.compile('&(?:([a-zA-Z0-9_\-]+)=([a-zA-Z0-9_\-]+))').findall(url)
	if m:
		return dict(m)


allow_cmds = {
	'list':list_files, 'refresh':refresh_list, 
	'get':get_files, 'status':status, 
	'quit':byebye, 'help':show_help, 'share':share_pomar,
	'join':join_pomar, 'alias':alias, 'get':get_files, 
	'debug':debug, 'info':info, 'cleartoc':clear_toc,
	'forget':forget_peer, 'who':who,
}

def parse_input(input):
	"""Parses the input string and evaluates against the allow_cmds dictionary 
	by executing existing key/value matches."""
	req_args = input.split()

	if req_args == []:
		return

	cmd = req_args[0]
	if allow_cmds.has_key(cmd):
		func = allow_cmds[cmd]
		args = req_args[1:] 
		func(args)


def run():
	c = client.Client(request_queue)
	c.setDaemon(True)
	c.start()


	while True:
		input = raw_input("--> ")
		parse_input(input)


