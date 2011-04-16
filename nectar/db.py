"""The Database module.
It serves a threaded sqlite3 database and tries to overtake the locking limitations on writes.
based on http://code.activestate.com/recipes/526618/
"""

import threading
import sqlite3
import os
import Queue

databases = {}

class DB(threading.Thread):
	"""Starts a database thread given a path for a sqlite database, an initialisation SQL and a thread name"""

	def __init__(self, db_path, init_sql=None, name=None):
		threading.Thread.__init__(self, name=name)
		self.queue = Queue.Queue()
		self.db_path = db_path
		self.init_sql = init_sql

		self.setDaemon(True)
		self.start()

	def execute(self, sql, args=None, result=None):
		"""Execute sql and write into the database"""
		if args == None:
			self.queue.put((sql, (), result))
		else:
			self.queue.put((sql, args, result))

	def select(self, sql, args=None):
		"""Execute read-only sql"""
		results = Queue.Queue()
		self.execute(sql, args, result=results)

		while True:
			out = results.get()

			if out == '!empty!':
				break

			yield out

	def close(self):
		"""Close connection to database"""
		self.execute('!close!')
		
	def run(self):
		"""Run thread"""

		if os.path.exists(self.db_path):
			self.db = sqlite3.connect(self.db_path)
			self.cursor = self.db.cursor()
		else:
			self.db = sqlite3.connect(self.db_path)
			self.cursor = self.db.cursor()

			if self.init_sql:
				self.cursor.execute(self.init_sql)
				log.log('created database: %s' % self.db_path)

		while True:
			sql, args, result = self.queue.get()

			if sql == '!close!':
					break

			self.cursor.execute(sql, args)

			
			if result:
				for row in self.cursor:
					result.put(row)
				result.put('!empty!')
			else:
				self.db.commit()

		self.cursor.close()


def start_db(db_name, db_path, init_sql=None):
	"""Start a database given a name, path to sqlite database and initialisation SQL"""
	if db_name not in databases:
		d = DB(db_path, init_sql, name=db_name)
		databases[db_name] = d
		return d
	else:
		raise DatabaseExists("Database with name '%s' already exists!" % db_name)
	

def stop_db(db_name):
	"""Stop a database given a name"""
	if db_name in databases:
		d = databases[db_name]
		d.close()
		del databases[db_name]
	else:
		raise DatabaseDoesNotExist("Database with name '%s' does not exist!" % db_name)

def get_db(db_name):
	"""Return a database instance given a name"""
	return databases[db_name]


class DatabaseExists(Exception):
	def __init__(self, value):
		self.value = value
	
	def __str__(self):
		return repr(self.value)

class DatabaseDoesNotExist(Exception):
	def __init__(self, value):
		self.value = value
	
	def __str__(self):
		return repr(self.value)


if __name__ == '__main__':
	"""this is a test."""

	import sys

	start_db('toc', sys.argv[1])
	start_db('resolv', sys.argv[2])

	print databases
	tocs = get_db('toc')
	resolv = get_db('resolv')

	for row in tocs.select("""select uuid,listversion from toc where pomar=? group by uuid having max(listversion)""",
		('/downloads/',)):
		print row

	for row in tocs.select('select * from toc'):
		print row

	for row in resolv.select("""select * from uuid"""):
		print row
	
	resolv.execute("""insert or replace into uuid (id, url, timestamp) values (?, ?, datetime())""", ('test', 'http://test.com:8080'))

	for row in resolv.select("""select * from uuid"""):
		print row

	print databases
	stop_db('toc')
	print databases
	stop_db('resolv')
	print databases
