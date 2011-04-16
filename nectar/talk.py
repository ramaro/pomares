"""The talk.py module includes all the communication logic between pomares peers."""

import re
import zlib
import base64
import os
import time

import resolver
import toc
from file import File, file_chunk, hash_buffer
from serialize import pack, unpack
import config 
from client import Request, file_objs
from cli import request_queue
import log

regex_accept_encoding = re.compile('\w+')
open_files = {}

def keys_exist(args, keyList):
	"""Returns True if all keys in keyList exist in args."""
	val = True
	for key in keyList:
		val = val and args.has_key(key)

	return val
	

def client_compressed(handler):
	"""Returns whether a client is sending compressed data"""
	compressed = False

	if handler.headers.has_key('accept-encoding'):
		if 'deflate' in regex_accept_encoding.findall(handler.headers['accept-encoding']):
				compressed = True

	return compressed

def server_compressed(handler):
	"""Returns whether a server	is sending compressed data"""
	compressed = False

	if handler.session.headers.has_key('content-encoding'):
		if 'deflate' in regex_accept_encoding.findall(handler.session.headers['content-encoding']):
				compressed = True

	return compressed

def openfile_for(hash):
	"""Return an open fileobj from the server's open dict"""
#	print 'open', hash
	try:
		fileobj, _ = open_files[hash]
		open_files[hash] = (fileobj, time.time())
		return fileobj
	except KeyError:
		return None

def newfile_for(hash, fileobj):
	"""Update the server's open dict with hash and fileobj"""
	open_files[hash] = (fileobj, time.time())

	return fileobj

def close_openfiles():
	"""Close any unused open files in the server's open dict"""
	del_list = []
	for hash in open_files:
		if (time.time() - open_files[hash][1] ) > config.openfile_time:
			open_files[hash][0].close()
			del_list.append(hash)

	for hash in del_list:
		del open_files[hash]

def new_fileobj(hash):
	"""Returns a new client file object for a hash"""
	results = toc.whoHas(hash)

	value = None
	for res in results:
		value = res
		break

	if value is None:
		raise Exception('couldnt find file in toc:%s.' % hash)

	pomares_id, filename, filesize, dirname, pomar = value #grab the first result
	download_dir = os.path.join(config.download_path, dirname)
	relpath = os.path.relpath(download_dir, config.download_path)

	if re.compile('^\.\.').match(relpath) or os.path.isfile(download_dir):
		print 'invalid final download dir: %s' % download_dir.encode(config.filename_encoding)
		return None

	try:
		os.makedirs(download_dir)
	except OSError:
		print ('final download dir already exists: %s' % download_dir.encode(config.filename_encoding))
		#return None

	download_filepath = os.path.join(download_dir, filename)
	relpath = os.path.relpath(download_filepath, config.download_path)

	if re.compile('^\.\.').match(relpath) or os.path.isfile(download_filepath):
		print 'invalid or final file already exists in download path: %s' % download_filepath.encode(config.filename_encoding)
		return None
	return File(download_filepath, filesize, hash)

def fileobj_for(hash):
	if file_objs.has_key(hash):
		return file_objs[hash]


	fobj = new_fileobj(hash)
	if fobj:
		file_objs[hash] = fobj
		return fobj

	raise Exception('coudlnt create file')
	

def to_client(handler):
	"""Decides what to send to a client given a handler object.
	Returns False on bad requests."""


	request_dict = {'LIST':request_client_LIST, 'FILE':request_client_FILE, 'PLIST':request_client_PLIST,
			'RESOLV':request_client_RESOLV,
	}

	handler.pomares_id = None
	if handler.request_args.has_key('pomares_id'):
		handler.pomares_id = handler.request_args['pomares_id']
	
	try:
		request_dict[handler.request_op](handler)

	except KeyError:
		handler.push_status(400, 'Bad Request')
		log.log("sent a 400 Bad Request response.")

		return False

def request_client_LIST(handler):
	compress = client_compressed(handler)
	buffer = pack('LIST', toc.lastUpdates(handler.request_pomar, all_rows=True))

	if compress:
		buffer = zlib.compress(buffer)

	handler.push_status(200, 'OK', size=len(buffer), compress=compress)

	handler.push(buffer)


def request_client_PLIST(handler):
	if keys_exist(handler.request_args, ('from', 'to')):
		compress = client_compressed(handler)
		buffer = ''
		if handler.pomares_id:
			buffer = pack('PLIST', toc.listVersion(handler.pomares_id, 
				(handler.request_args['from'], handler.request_args['to']), handler.request_pomar, all_rows=True))
		else:
			buffer = pack('PLIST', toc.listVersion(config.my_uuid, 
				(handler.request_args['from'], handler.request_args['to']), handler.request_pomar, all_rows=True))

		if compress:
			buffer = zlib.compress(buffer)

		handler.push_status(200, 'OK', size=len(buffer), compress=compress)
		handler.push(buffer)

	else:
		handler.push_status(400, 'Bad Request')


def request_client_FILE(handler):
	if keys_exist(handler.request_args, ('hash', 'chunk')):
		filename_size = toc.pathFor(handler.request_args['hash'], handler.request_pomar)
		fileobj = openfile_for(handler.request_args['hash'])
		
		compress = client_compressed(handler)
		if filename_size is not None and handler.request_args['chunk'].isdigit():
			path, size = filename_size
			chunk, f = file_chunk(path, size, int(handler.request_args['chunk']), compress=compress, fileobj=fileobj)

			if fileobj is None:
				newfile_for(handler.request_args['hash'], f)

			# Send a 204 when there's no data to send:
			if chunk is None or chunk.size is 0:
				handler.push_status(204, 'No Content')
				return

			if compress:
				log.log('pushing compress FILE %s %dbytes chunk %d (%dbytes)'%(path, size, int(handler.request_args['chunk']), 
						len(chunk)) )
			else:
				log.log('pushing FILE %s %dbytes chunk %d (%dbytes)'%(path, size, int(handler.request_args['chunk']),
						len(chunk)) )

			handler.push_status(200, 'OK', size=len(chunk), compress=compress)
			handler.push(chunk.buffer)
		else:
			handler.push_status(204, 'No Content')
	else:
		handler.push_status(400, 'Bad Request')


def request_client_RESOLV(handler):
	if handler.pomares_id:
		who = resolver.resolve(handler.pomares_id)

		if who:
			buffer = pack('RESOLV',(handler.pomares_id, who))
			handler.push_status(200, 'OK', size=len(buffer))
			handler.push(buffer)
		else:
			handler.push_status(204, 'No Content')
	else:
		handler.push_status(400, 'Bad Request')
		

def to_server(handler):
	"""Decides what to do with a servers reply given a handler object.
	Returns False on bad requests."""

	#print zlib.decompress(handler._buffer_in)

	request_dict = {'LIST':request_server_LIST, 'FILE':request_server_FILE, 'PLIST':request_server_PLIST,
			'RESOLV':request_server_RESOLV,
	}

	handler.pomares_id = None
	if handler.request.args.has_key('pomares_id'):
		handler.pomares_id = handler.request.args['pomares_id']

	if handler.session.http_status != '200':
		log.log("client received http status %s" % handler.session.http_status)
		return False
	
	try:
		request_dict[handler.request.type](handler)

	except KeyError:
		log.log("client received unknown request type")
		return False

def request_server_LIST(handler):
	"""Updates the TOC when given a LIST reply buffer."""

  	if server_compressed(handler):
		handler._buffer_in = zlib.decompress(handler._buffer_in)

	buffer = unpack(handler._buffer_in)
	url = handler.request.internal['url']
	pomar = handler.request.pomar
	pomares_id = None

	try:
		pomares_id = handler.session.headers['pomares-id']
	except KeyError:
		raise KeyError('pomares-id missing client session headers')

	if not buffer.has_key('LIST'):
		raise KeyError('LIST request type not present')


	#Update url timestamp
	resolver.update(pomares_id, '%s://%s' % (handler.request.parsed_url.scheme, handler.request.parsed_url.netloc))

	for recvd_pomares_id, recvd_list_version in buffer['LIST']:
		recvd_url = resolver.resolve(recvd_pomares_id)

		if recvd_url:
			recvd_from_version = toc.lastVersionFor(recvd_pomares_id, pomar=pomar)

			if recvd_from_version is None:
				recvd_from_version = 0 

			recvd_versions = (recvd_from_version, recvd_list_version)
			recvd_versions = (min(recvd_versions), max(recvd_versions))

			#only Request a PLIST if our version is inferior:
			if recvd_versions[0] < recvd_versions[1]:
				req = Request('PLIST', {'from':recvd_versions[0],'to':recvd_versions[1]}, internal={'url':recvd_url})
				req.pomar = pomar
				request_queue.put(req)
		else:
			#mark as unknown:
			resolver.update(recvd_pomares_id, None)

			#and request a RESOLV:
			req = Request('RESOLV', {'pomares_id':recvd_pomares_id}, internal={'url':url} )
			request_queue.put(req)


	print 'client LIST'

def request_server_FILE(handler):
	if server_compressed(handler):
		handler._buffer_in = zlib.decompress(handler._buffer_in)

#	try:
	buffer = unpack(handler._buffer_in)
#	except ValueError:
#		print '_buffer_in', handler._buffer_in, 'buffer_in', handler.buffer_in
#		print handler.session.headers
#		print handler.session.read_bytes
#

	pomar = handler.request.pomar
	pomares_id = None
	filepath = None

	try:
		pomares_id = handler.session.headers['pomares-id']
	except KeyError:
		raise KeyError('pomares-id missing client session headers')


	if not buffer.has_key('FILE'):
		raise KeyError('FILE request type not present')


	#Update url timestamp
	resolver.update(pomares_id, '%s://%s' % (handler.request.parsed_url.scheme, handler.request.parsed_url.netloc))

	#try:
	chunk_number, buffer, hash  = buffer['FILE']
	buffer = base64.b64decode(buffer)
	
	#print 'check', handler.request.args['chunk'], chunk_number, hash_buffer(buffer), hash
	if handler.request.args['chunk'] == chunk_number and hash_buffer(buffer) == hash:
		file_obj = fileobj_for(handler.request.args['hash'])
		if file_obj:
			file_obj.update(buffer, chunk_number*config.chunk_size)
			filepath = file_obj.path
			#print 'wrote chunk', chunk_number
			return True #update succesful
		else:
			print 'couldnt create file at chunk', chunk_number
			return False #couldnt create a File

	else:
		print 'couldnt update file, checksum failed'
		return False #update failed

	#except:
#		log.log('could not write FILE chunk %d for %s' % (chunk_number, filepath))
	return None #update error
	


	print 'client FILE'

def request_server_PLIST(handler):
	"""Updates the TOC when given a PLIST reply buffer."""

	if server_compressed(handler):
		handler._buffer_in = zlib.decompress(handler._buffer_in)

	buffer = unpack(handler._buffer_in)
	url = handler.request.internal['url']
	pomar = handler.request.pomar
	pomares_id = None

	try:
		pomares_id = handler.session.headers['pomares-id']
	except KeyError:
		raise KeyError('pomares-id missing client session headers')

	if not buffer.has_key('PLIST'):
		raise KeyError('PLIST request type not present')


	#Update url timestamp
	resolver.update(pomares_id, '%s://%s' % (handler.request.parsed_url.scheme, handler.request.parsed_url.netloc))

	for recvd_filename, recvd_size, recvd_hash, recvd_pomares_id, recvd_path, recvd_listversion in buffer['PLIST']:
		#TODO: deprecate from:to and use only one version number in hex or other cool format

		toc.update({'filename':recvd_filename, 'size':recvd_size, 'hash':recvd_hash, 'uuid':recvd_pomares_id,
					'dirname':recvd_path, 'listversion':recvd_listversion}, 
					pomar) 

		recvd_url = resolver.resolve(recvd_pomares_id)

		if recvd_url is None:
			resolver.update(recvd_pomares_id, None)
			req = Request('RESOLV', {'pomares_id':recvd_pomares_id}, internal={'url':url} )
			request_queue.put(req)
		

	print 'client PLIST'

def request_server_RESOLV(handler):
	"""Updates the TOC when given a RESOLV reply buffer."""

	if server_compressed(handler):
		handler._buffer_in = zlib.decompress(handler._buffer_in)

	buffer = unpack(handler._buffer_in)
	url = handler.request.internal['url']
	pomar = handler.request.pomar
	pomares_id = None

	try:
		pomares_id = handler.session.headers['pomares-id']
	except KeyError:
		raise KeyError('pomares-id missing client session headers')

	if not buffer.has_key('RESOLV'):
		raise KeyError('RESOLV request type not present')


	#TODO: create a probabilistic way to determine if a RESOLV value is good 
	#by comparing with other RESOLV values for the same query
	#for now... it's just plain stupid

	recvd_pomares_id, recvd_url = buffer['RESOLV']
	#Update url timestamp
	resolver.update(recvd_pomares_id, recvd_url)


	print 'client RESOLV'
