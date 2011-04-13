#!/usr/bin/env python

import getopt, sys, signal
import nectar.server, nectar.cli

def usage():
	print """Usage: %s [options]
Pomares is a private file distribution system.

	-h, --help	for this message
	-c, --client	run client only
	-s, --server	run server only
	-d, --debug	debug to stdout
""" % sys.argv[0]

def handler(signum, frame):
	print 'signal', signum, 'caught.'
	sys.exit()


def init_signals():
	signal.signal(signal.SIGINT, handler )
	


def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hcsd", ["help", "client", 
		"server", "debug"])
	
	except getopt.GetoptError, err:
		print str(err)
		usage()
		sys.exit(2)

	client_only=True
	server_only=True
	debug=False

	for option, value in opts:
		if option in ("-h", "--help"):
			usage()
			sys.exit()

		elif option in ("-c", "--client"):
			server_only=False

		elif option in ("-s", "--server"):
			client_only=False

		elif option in ("-d", "-v", "--debug", "--verbose"):
			debug=True

	#print client_only, server_only, debug
	
	init_signals()

	if server_only:
		s = nectar.server.Server()
		s.setDaemon(True)
		s.start()

	if client_only:
		c = nectar.cli.run()




if __name__ == "__main__":
	main()



