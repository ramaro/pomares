"""
The server module.
It is a stripped down HTTP server that only replies to pomares specific requests.
"""
import select
import socket
import threading
import time
import re

import log
import config
import talk

regex_GET = re.compile('^GET (/\S+) HTTP/...$')
regex_OPTIONS = re.compile('^(\S+)[:] ?([\S\ ]+)?')
regex_requested = re.compile('^(/?[a-zA-Z0-9_\-/]*/)?\?request=([a-zA-Z0-9_\-]+)(&.*)?$')
regex_requested_args = re.compile('&([a-zA-Z0-9_\-]+=[a-zA-Z0-9_\-]+)')

class Server(threading.Thread):
	"""The Server class is a stripped down HTTP server that only replies 
	to pomares specific requests."""

	def __init__(self,port=8080, bind_address='', backlog=1024):
		threading.Thread.__init__(self)

		self.server_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server_fd.bind((bind_address, port))
		self.server_fd.listen(backlog)

		self.input_fds = [self.server_fd, ]
		self.output_fds = []
		self.handlers = {}
		self.timeout = 60


	def del_handler(self, handler, close=True):
		if close:
			handler.fd.close()

		log.log('closed: '+str(handler.address))
		try:
			self.input_fds.remove(handler.fd)
		except:
			pass

		try:
			self.output_fds.remove(handler.fd)
		except:
			pass

		log.log('deleted: '+str(handler.address))
		del self.handlers[handler.fd]



	def run(self):
		while True:
			if len(self.handlers) > 0:
				log.log(str(len(self.handlers))+ ' handlers')

			inputready_fds, outputready_fds, xready_fds = select.select(self.input_fds, 
			self.output_fds, [], self.timeout)


			if (inputready_fds, outputready_fds, xready_fds) == ([],[],[]):
				# We've got a timeout here,
				# let's get rid of all the silent handlers:
				for h in self.handlers.values():
					if time.time() - h.time >= self.timeout:
						self.del_handler(h)

				#let's close all unused open files...
				talk.close_openfiles()
				continue



			for fd in inputready_fds:

				if fd == self.server_fd:
					# On new connections:
					_fd, _address = self.server_fd.accept()
					handler = Handler(_fd, _address)
					self.handlers[_fd] = handler
					self.input_fds.append(_fd)

					log.log('connected: '+ str(handler.address))

				else:
					# On anything else
					handler = self.handlers[fd]
					try:
						handler.buffer = fd.recv(config.server_recv_buffer)
						#FIXME: not catching connection resets here....
						#error: [Errno 54] Connection reset by peer
					except socket.exception:
						handler.buffer = ''

					if handler.buffer:
						#log.log('received: '+handler.buffer+' from: '+handler.address)
						valid = handler.valid_input()

						if valid is None:
							continue

						if not valid:
							self.del_handler(handler)
							continue

						if valid:
							log.log('handler.process_response()')

							#self.input_fds.remove(handler.fd)
							self.input_fds.remove(fd)

							handler.process_response()

							#if handler.response is not None:
								#self.output_fds.append(handler.fd)
							self.output_fds.append(fd)

					else:
						# Close() and remove fd from input and ouput watch lists:
						self.del_handler(self.handlers[fd])


			# Check and write to output fds:
			for fd in outputready_fds:
				#if self.handlers[fd].response is None:
				#	print 'response is None'
				 
				log.log('writing to: '+str(self.handlers[fd].address))
				fd.sendall(
					self.handlers[fd].response[
					self.handlers[fd].sent_bytes:self.handlers[fd].sent_bytes + 
					config.chunk_size])
				self.handlers[fd].sent_bytes += config.chunk_size

				if self.handlers[fd].sent_bytes >= len(self.handlers[fd].response):
					self.handlers[fd].response = None
					self.handlers[fd].sent_bytes = 0
					#self.input_fds.append(handler.fd)
					self.input_fds.append(fd)
					#try:
					#print fd, handler.fd
					#self.output_fds.remove(handler.fd)
					self.output_fds.remove(fd)
					#except ValueError:
					#	pass
				

class Handler:
	"""The Handler class serves as a channel to each client.
	It also keeps the clients session, response buffer and original request."""

	def __init__(self, fd, address):
		self.fd = fd
		self.address = address
		self._buffer = ''
		self.buffer = ''
		self.time = time.time()
		self.request = None
		self.headers = {}
		self.response = None
		self.pomares_id = None
		self.sent_bytes = 0
		self.request_pomar = None
		self.request_op = None
		self.request_args = None
		self.open_files = {}


	def parsed_request(self):
		try:
			pomar, op, args = regex_requested.findall(self.request_resource)[0]
			self.request_pomar = pomar
			self.request_op = op 
			self.request_args = {}

			if args != '':
				for arg in regex_requested_args.split(args):
					if arg != '':
						k,v = re.split('=', arg)
						self.request_args[k] = v
			
			return True
		except:
			log.log("request did not match: "+self.request_resource)
			return False

	def valid_input(self, request_limit=1024):
		"""Validates the input buffer for any valid/sane data/requests.
		Data in buffer gets internally appended and is then emptied.
		Returns None if not enough data, True if valid, False otherwise."""
		self.request_resource = None

		if len(self.buffer) > 0:
			self._buffer += self.buffer
			self.buffer = ''

		if len(self._buffer) <= request_limit:
			split_buffer = self._buffer.split("\r\n\r\n") 
			# log.log('split_buffer: '+ split_buffer)

			if len(split_buffer) >= 2:
				if split_buffer[-1] is '':
					# We have a crlfcrlf terminated request, let validate.
					# Validate GET request and headers...
					split_buffer = split_buffer[0].split("\r\n")
					#log.log('split_buffer: '+split_buffer)
					if len(split_buffer) > 0:
						if regex_GET.match(split_buffer[0]):
							self.request = split_buffer[0]
							self.request_resource = regex_GET.findall(self.request)[0]
							for header in split_buffer[1:]:
								if regex_OPTIONS.match(header):
									k, v = regex_OPTIONS.findall(header)[0]
									self.headers[k.lower()] = v

						else:
							return False #no healthy GET
					else:
						return False #no healthy GET


					log.log('request: '+self.request)
					log.log('headers: '+str(self.headers))

					return self.prepared()
					#return True

				else:
					# Not crlfcrlf terminated, not enough data.
					return None
		else:
			# Request too big not to have validated by now. Invalid.
			return False

	def prepared(self):
		"""Run stuff before interacting with client.
		Returns True if successful."""

		return self.parsed_request()

		

	def process_response(self):
		"""Prepares the response by processing the request
		and writing the handler response buffer.
		"""

		self.time = time.time()
		self._buffer = ''
		client_response = talk.to_client(self)
		#print 'process_response', client_response

		return client_response


	def push(self, data):
		"""Push data into the clients buffer."""

		self.response += data

	def push_status(self, http_code, status_msg, extra='', size=0, compress=False):
		"""Push HTTP status, code, message and size and other info to clients buffer."""

		content_length = ''

		if size > 0:
			content_length = 'Content-Length: %d\r\n' % size

		if compress:
			self.response = "HTTP/1.0 %d %s\r\n\
Content-Type: application/json\r\n\
Server: Pomares/SVN\r\nPomares-ID: %s\r\n\
Content-Encoding: deflate\r\n\
%s\
Connection: Keep-Alive\r\n\r\n%s" % (http_code, status_msg, config.my_uuid, 
			content_length, extra)
			return


		self.response = "HTTP/1.0 %d %s\r\n\
Content-Type: application/json\r\n\
Server: Pomares/SVN\r\nPomares-ID: %s\r\n\
%s\
Connection: Keep-Alive\r\n\r\n%s" % (http_code, status_msg, config.my_uuid, 
		content_length, extra)

