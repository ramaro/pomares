"""This module includes the File (and maybe others) class which _tries_ to take care of creating/updating sparse files in a portable way."""
import re
import hashlib
import base64
import os
from cStringIO import StringIO
import zlib

import log
from config import chunk_size
from serialize import pack

class OffsetError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)


class File():
	def __init__(self, path, size, hash):
		self.path = path
		self.size = size
		self.hash = hash

		if not os.path.exists(path):
			log.log('created file %s' % path)
			self.fd = open(path, 'w')
		else:
			self.fd = open(path, 'r+')

	def update(self, buffer, offset):
		if offset+len(buffer) > self.size:
			raise OffsetError('Can\'t write offset %d and buffer length %d on a file size of %d bytes' % (offset, len(buffer), self.size))
						
		self.fd.seek(offset)
		self.fd.write(buffer)
		log.log('wrote offset %d to %s' % (offset, self.path))
		
	def __del__(self):
		log.log('closing %s' % self.path)
		self.fd.close()

	
def hash(filename):
	"""Returns the md5 hexed digest for filename."""
	m = hashlib.md5()
	with open(os.path.expanduser(filename), 'r') as f:
		data = True
		while data:
			data = f.read(8192)
			m.update(data)

	return m.hexdigest()

def hash_buffer(buffer):
	"""Returns de md5 hexed digest for a buffer."""
	m = hashlib.md5()
	m.update(buffer)

	return m.hexdigest()
		
	
def list(pathname, unroot=True):
	"""Returns a dictionary of files in pathname. Setting unroot to True strips the pathname from its entries"""
	fileList = []
	pathname = os.path.expanduser(pathname)
	for root, dirs, files in os.walk(pathname):
		for file in files:
			full_path = os.path.join(root, file)
			if os.path.isfile(full_path) and os.access(full_path, os.R_OK):
				file_size = int(os.path.getsize(full_path))
				file_hash = hash(full_path)
				if unroot:
					full_path = re.sub(r'%s/*' % pathname, '', full_path)
					fileList.append((file_hash, (full_path, file_size)))
				else:
					fileList.append((file_hash, (full_path, file_size)))
	return dict(fileList)

def chunk_list(file_size):
	"""Calculates the number of possible chunks for a given file_size"""
	chunks = [chunk_size] * (file_size / chunk_size)
	if file_size%chunk_size > 0:
		chunks.append((file_size % chunk_size))

	return chunks

def file_chunk(filepath, file_size, chunk_number, compress=False, fileobj=None):
	"""Returns a Chunk object and its fileobj."""

	possible_chunks = (file_size / chunk_size) + (file_size % chunk_size)
	if chunk_number >= possible_chunks or chunk_number < 0: 
		return None

	if fileobj:
		f = fileobj
	else:
		f = open(filepath, 'r')
		#print 'open!'

	f.seek(chunk_size*chunk_number)
	buff = f.read(chunk_size)

	#if fileobj is None:
	#	f.close() #TODO: have file descriptor on handlers sessions

	return Chunk(buff, number=chunk_number, compress=compress), f

class Chunk:
	
	def __init__(self, data, number, compress=False):
		self.number = number
		self.hash = hash_buffer(data)
		self.size  = len(data)
		if compress:
			self.buffer = zlib.compress(pack('FILE', (self.number, base64.b64encode(data), self.hash)))
		else:
			self.buffer = pack('FILE', (self.number, base64.b64encode(data), self.hash))

	def __repr__(self):
		return self.buffer

	def __len__(self):
		return len(self.buffer)
	
