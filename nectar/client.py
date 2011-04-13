import threading
import Queue
import select
import urlparse
import socket
import time
import operator
import re
import StringIO

import toc
import config
import log
import talk

regex_HTTP = re.compile('^HTTP/1\.\d +(\d+) +([\w ]+)\r\n')
regex_HEADERS = re.compile('^(\S+):([\S ]+)\r\n')
regex_END = re.compile('^\r\n')

file_objs = {}

class Request:
	def __init__(self, type, args, internal={}):
		"""Represents a pomares request type, args is a dictionary with request arguments, 
		internal includes funcionality passing options (usually within the interface)."""

		self.type = type
		self.args = args
		self.internal = internal
		self.address = None
		self.pomar = None
		self.parsed_url = None

		if self.internal.has_key('url'):
			self.update_url(self.internal['url'])

	def update_url(self, url, pomar=None):
		self.parsed_url = urlparse.urlparse(url)
		self.pomar = self.parsed_url.path

		if self.parsed_url.port is None:	
			self.address = (self.parsed_url.hostname, 80)
		else:
			self.address = (self.parsed_url.hostname, self.parsed_url.port)

		if pomar != None:
			self.pomar = pomar


def address_for(url):
	parsed_url = urlparse.urlparse(url)

	if parsed_url.port is None:	
		return (parsed_url.hostname, 80)
	else:
		return (parsed_url.hostname, parsed_url.port)


class Session:
	def __init__(self):
		self.read_bytes = 0
		self.headers = {}
		self.http_status = None
		self.http_response = None


class Handler:
	def __init__(self, request):
		self.time = time.time()

		self.buffer_in = ''
		self._buffer_in = ''
		self.buffer_out = ''
		self.session = None
		self.request = None #current request
		self.address = None #current address

		self.fd = socket.create_connection(request.address)

	def busy(self):
		if self.request is None:
			return False

		if self.session is not None:
			return True

		if self._buffer_in is not '' or self.buffer_out is not '':
			return True

	def cleanup(self):
		self.buffer_in = '' 
		self._buffer_in = '' 
		self.session = None
		self.request = None
		self.buffer_out = ''

	def process_request(self, request):
		"""Processes and prepares the next request in the handler request queue.
		Returns the process request, None if handler request queue is empty."""
		log.log('client process_request()')
		log.log('client processing'+ str(request))
		self.request = request
		self.address = request.address

		self.prepare_request(request)

		return request
	
	def prepare_request(self, request):
		"""Prepares and writes the HTTP request into the output buffer.""" 

		log.log('client prepare_request()')
		_headers =  {'User-Agent':'Pomares/SVN', 'Pomares-ID':config.my_uuid,
						#'Host':'%s:%d'% request.address}
						'Accept-Encoding':'deflate', 'Host':'%s:%d'% request.address}

		if request.internal.has_key('debug'):
			_headers['-DEBUG-']=request.internal['debug']

		headers = '\r\n'.join(['%s: %s' % (k, v) for k, v in _headers.items()])

		if request.args and request.args.items():
			args = '&'.join(['%s=%s' % (k, str(v)) for k, v in request.args.items()])
			self.buffer_out = 'GET %s?request=%s&%s HTTP/1.0\r\n%s\r\n\r\n' % \
											(request.pomar, request.type, args, headers)


		#a request with no args (like LIST): 
		else:
			request.args = {}
			self.buffer_out = 'GET %s?request=%s HTTP/1.0\r\n%s\r\n\r\n' % \
											(request.pomar, request.type, headers)

		if request.internal.has_key('debug'):
			print '\nDEBUG sending:', repr(self.buffer_out)


	def valid_input(self, response_limit=1024):
		"""validates the input buffer by matching server response.
		response_limit is the size limit for a healthy server header response.
		Returns False if not valid, a Session otherwise. None if not enough data.
		"""

		if len(self.buffer_in) > 0:
			self._buffer_in +=  self.buffer_in
			self.buffer_in = ''

		s = StringIO.StringIO(self._buffer_in)
		validated = Session()
		OK_data = False

		for n, line in enumerate(s):
			if n is 0:
				#match HTTP/1.0 line and store in dict:
				m = regex_HTTP.match(line)
				if m:
					validated.http_status = m.groups()[0]
					validated.http_response = m.groups()[1]
			
			else:
				#match (Key: Value)*\r\n and store in dict:
				m = regex_HEADERS.match(line)
				if m:
					#all header fieldnames are converted to lower case for compliance
					validated.headers[m.groups()[0].lower().strip()] = m.groups()[1].strip()

				#match end of server headers:
				m = regex_END.match(line)
				if m:
					OK_data = s.pos
					break

		s.close()

		if OK_data:
			if self.request.internal.has_key('debug'):
				print 'DEBUG received response headers:', repr(self._buffer_in[:OK_data])

			#update buffer's position for the start of response data
			self._buffer_in = self._buffer_in[OK_data:]

			return validated

		else:
			if len(self._buffer_in) < response_limit:
				return None #Not enough data
			else:
				return False #This data's no good

	def process_response(self):
		"""Processes the servers response."""

		#at this point, self._buffer_in must be complete
		#all response is in self._buffer_in, self.buffer_in is empty as of now

		ret =  talk.to_server(self)

		if self.request.internal.has_key('debug'):
			print 'DEBUG received data(', len(self._buffer_in),'bytes)', repr(self._buffer_in)
			print 'DEBUG bytes read',self.session.read_bytes  

		self.cleanup()


	def __del__(self):
		self.fd.close()

class Client(threading.Thread):
	
	def __init__(self, request_queue):
		threading.Thread.__init__(self)
		self.input_fds = []
		self.output_fds = []
		self.queue = request_queue
		self.handlers_addr = {} #handler dict by address key
		self.handlers_fd = {} #handler dict by fd key
		self.timeout = 1

		self.input_fds = []
		self.output_fds = []

	#this broken, does not properly distribute requests over handlers. FIXME 
	def handler_for(self, request):
		"""Returns a new/existing non-busy handler for a request"""

		#FILE requests have no determined address:
		if request.type is 'FILE' and request.address is None:
				tocs = toc.TOC()
				resolv = toc.Resolver()

				#FIXME this should be a lazy check and should cache in memory every x secs...SLOW
				#using whoHas is not good...should write a proxy function...
				#also need to use indexes on tables....
				results = tocs.whoHas(request.args['hash'])
				busy_url = None

				for pomares_id, filename, filesize, dirname, pomar in results:
					url = resolv.resolve(pomares_id)

					if url:
						address = address_for(url)

						#Prioritise unconnected peers
						if not self.handlers_addr.has_key(address):
							request.update_url(url, pomar=pomar)
							break
						else: #try a connected, not busy one
							for h in self.handlers_addr[address]:
								if not h.busy():
									request.update_url(url, pomar=pomar)
									break
								else:
									busy_url = url, pomar

				#if we get here, add a busy one:
				if request.address is None:
					request.update_url(busy_url[0], busy_url[1])


		if request.address and self.handlers_addr.has_key(request.address):
			handlers_addr = self.handlers_addr[request.address]
			log.log('client possible handlers_addr:'+ str(handlers_addr))
			for h in handlers_addr:
				log.log(str(h)+ 'busy:'+ str(h.busy()) )

			if len(handlers_addr) < config.max_connections:
				self.new_handler(request)
				

			free_handlers = filter(lambda h: h.busy() is False, handlers_addr)

			if free_handlers:
				return free_handlers[0]
			else:
				return None

		else:
			return self.new_handler(request)

	def new_handler(self,request):
		log.log('client creating a new handler...')


		#print 'new_handler', request.address, request.parsed_url, request.type, request.args, request.pomar
		
		handler = Handler(request)
		self.handlers_fd[handler.fd] = handler

		if self.handlers_addr.has_key(request.address):
			self.handlers_addr[request.address].append(handler)
		else:
			self.handlers_addr[request.address] = [handler, ]

		return handler
	
	def del_handler(self, handler, close=True):
		if close:
			handler.fd.close()
			log.log('client closed: '+str(handler.fd))

		try:
			self.input_fds.remove(handler.fd)
		except ValueError:
			pass

		try:
			self.output_fds.remove(handler.fd)
		except ValueError:
			pass

		try:
			handlers = self.handlers_addr[handler.address]
			if len(handlers) > 0:
				handlers.remove(handler)

			if len(handlers) is 0:
				del self.handlers_addr[handler.address]
		except KeyError:
			pass
				
		try:
			del self.handlers_fd[handler.fd]
		except KeyError:
			pass



	def get_request(self):
		try:
			current_request = self.queue.get_nowait()
			#current_request = self.queue.get() #Block while testing run() without select()
			return current_request
		except Queue.Empty:
			return None


	def run(self):
		running = True

		while running:
			
#			if len(self.handlers_fd):
#				log.log('client handlers_fd: %s' % len(self.handlers_fd))
#
#			if len(self.handlers_addr):
#				log.log('client handlers_addr: %s' % len(self.handlers_addr))


			#FIXME: we should loop through X requests as long as there's free handlers...
			#FIXME: the queue must be changed... having everything in one queue is not efficient for multiple files...
			current_request = self.get_request()
			if current_request:
				handler = self.handler_for(current_request) 
				if handler:
					#the handler's socket must be checked for connect()ivity 
					#(probably the select() loop will take care of self.handlers_addr
					#this code block might be moved to the end)
					handler.process_request(current_request)
					log.log('handler:%s request:%s' % (str(handler), str(handler.request)))
				else:
					self.queue.put(current_request)


			self.input_fds = [fd for fd in self.handlers_fd]
			#must check if len(buffer_out) as if there's anything to send :
			self.output_fds = [fd for fd in self.handlers_fd if len(self.handlers_fd[fd].buffer_out) > 0] 

			inputready_fds, outputready_fds, xready_fds = select.select(self.input_fds, 
			self.output_fds, [], self.timeout)

			"""
			DEBUG
			if inputready_fds:
				print 'inputs:', inputready_fds
			if outputready_fds:
				print 'outputs:', outputready_fds
			"""
			
			#on outgoing
			for fd in outputready_fds:
				handler = self.handlers_fd[fd]

				if handler.buffer_out:
					log.log('client writing %dbytes to: %s' % 
							(len(handler.buffer_out), str(handler.request.address)))
					sent = fd.sendall(handler.buffer_out)

					#on a successful sendall() clear buffer_out:
					if sent is None:
						handler.buffer_out = ''

			#on incoming:
			for fd in inputready_fds:
				handler = self.handlers_fd[fd]
				
				#handle ongoing requests (current sessions):
				if handler.session:
					log.log('client current handler.session')
					content_length = handler.session.headers['content-length']

					if handler.session.read_bytes < content_length:
						if (content_length - handler.session.read_bytes) > config.client_recv_buffer:
							handler.buffer_in = fd.recv(config.client_recv_buffer)
							handler.session.read_bytes += len(handler.buffer_in)
							handler._buffer_in += handler.buffer_in
						else:
							if (content_length - handler.session.read_bytes) > 0:
								handler.buffer_in = fd.recv(content_length - handler.session.read_bytes)
								handler.session.read_bytes += len(handler.buffer_in)
								handler._buffer_in += handler.buffer_in

							if (content_length - handler.session.read_bytes) <= 0:
								#theres nothing to read anymore. Process:
								handler.buffer_in = ''

								#print content_length, handler.session.headers['content-length'], handler.session.read_bytes
								handler.process_response()
								log.log('client processed response')
					continue

				#handle new requests (new sessions):
				if not handler.session:
					log.log('client new handler.session')
					handler.buffer_in = fd.recv(config.client_recv_buffer)

					#on connection errors:
					if not handler.buffer_in:
						self.del_handler(handler)
						continue

					valid = handler.valid_input()

					if valid is None:
						continue

					if not valid:
						log.log('client not valid input')
						self.del_handler(handler)
						continue

					if valid:
						log.log('client handler.process_response()')
						handler.session = valid

						#Content-Length _must_ be present:
						if handler.session.headers.has_key('content-length'):
							handler.session.headers['content-length'] = int(handler.session.headers['content-length'])
							handler.session.read_bytes += len(handler._buffer_in)

						else:
							log.log('client content-length not provided, close()ing...')
							self.del_handler(handler)
							continue
						
						#Only process request when all content-length is read:
						#print handler.session.headers['content-length'], handler.session.read_bytes
						if handler.session.headers['content-length'] == handler.session.read_bytes:
								handler.process_response()


