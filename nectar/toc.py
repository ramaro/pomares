"""The Table of Contents module.
It keeps track of the history and locations of all files and peers."""

import config, os, sqlite3, log
from config import my_uuid

class TOC():
	"""The TOC (Table of Contents) class."""

	def __init__(self, toc_filepath=config.toc_file):
		if os.path.exists(toc_filepath):
			self.db = sqlite3.connect(toc_filepath)
			self.cursor = self.db.cursor()
		else:
			self.db = sqlite3.connect(toc_filepath)
			self.cursor = self.db.cursor()
			self.cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS "toc" (
			    "filename" TEXT NOT NULL,
			    "size" INTEGER NOT NULL,
			    "hash" TEXT NOT NULL,
			    "uuid" TEXT NOT NULL,
			    "dirname" TEXT NOT NULL,
			    "listversion" INTEGER NOT NULL,
			    "pomar" TEXT NOT NULL,
			    "timestamp" DATETIME NOT NULL,
			    PRIMARY KEY (filename, size, hash, uuid, dirname, pomar)	
			)
			"""
			)
			self.cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS "locations" (
			    "pomar" TEXT NOT NULL,
			    "pathname" TEXT NOT NULL,
			    PRIMARY KEY (pomar, pathname)
			)
			"""
			)

			self.cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS "peer_usage" (
			    "hash" TEXT NOT NULL,
			    "uuid" TEXT NOT NULL,
			    "pomar" TEXT NOT NULL,
			    "usage" INTEGER NOT NULL,
			    PRIMARY KEY (hash, uuid)
			)
			"""
			)
			
			self.db.commit()

			log.log('created toc database: %s' % toc_filepath)

	def __del__(self):
		self.db.close()

	def peerFor(self, hash):
		"""Returns an usage-evaluated uuid for a given hash."""

		self.cursor.execute("""
		insert or ignore into peer_usage (hash, uuid, pomar, usage) 
		select hash, uuid, pomar, 0 from toc where hash=? 
		group by pomar, uuid having max(listversion)
		""", (hash, )
		)
		self.db.commit()
		
		self.cursor.execute("""
		select uuid, pomar, usage from peer_usage 
		where hash=? and usage > -2 order by usage asc limit 1
		""", (hash, )
		)

		return self.cursor.fetchone()

	def peerSuccess(self, uuid, hash, success=True):
		"""Increases the usage counter for a specific peer and hash."""

		self.cursor.execute("""
		select usage from peer_usage
		where uuid=? and hash=?
		""", (uuid, hash,)
		)
		prev_usage = self.cursor.fetchone()

		if prev_usage is None:
			return

		new_usage = prev_usage[0]+1

		if not success:
			new_usage = prev_usage[0]-1

		self.cursor.execute("""
		update or ignore peer_usage
		set usage=?
		where uuid=? and hash=?
		""", (new_usage, uuid, hash)
		)

		print 'success', new_usage, uuid, hash, success
			
		self.db.commit()



	def lastVersionFor(self, pomares_id, pomar='/'):
		"""Returns the latest listversion for a pomares_id."""

		self.cursor.execute("""
		select max(listversion) from toc where uuid=? and pomar=?
		""", (pomares_id, sanitize_pomar(pomar))
		)

		val = self.cursor.fetchone()
		if val is not None:
			return val[0]
		
		return val

	def lastUpdates(self, pomar='/'):
		"""Returns a list of pomares-IDs and latest listversions."""

		self.cursor.execute("""
		select uuid,listversion from toc where pomar=? group by uuid having max(listversion)
		""", (sanitize_pomar(pomar),)
		)

		return self.cursor.fetchall()


	def listVersion(self, pomares_id, from_to, pomar='/'):
		"""Returns a list of files for a pomares_id between versions in from_to tuple"""
		
		self.cursor.execute("""
		select filename, size, hash, uuid, dirname, listversion from toc 
		where uuid=? and pomar=? and listversion between ? and ?
		""", (pomares_id, sanitize_pomar(pomar), from_to[0], from_to[1])
		)
		
		return self.cursor.fetchall()

	def whoHas(self, hash, orderByTime=True):
		"""Returns the uuids with respective filenames, filesizes, dirnames and pomar for hash."""

		order_string=""

		if orderByTime:
			order_string = "order by timestamp desc"

		self.cursor.execute("""
		select uuid, filename, size, dirname, pomar from toc where hash=? 
		group by pomar, uuid having max(listversion) %s
		""" % order_string, (hash,) 
		)

		return self.cursor.fetchall()

	def update(self, values, pomar='/', commit=True):
		"""Updates toc with values for dict {filename, size, hash, uuid, dirname, listversion, pomar}."""

		self.cursor.execute("""
		insert or ignore into toc (filename, size, hash, uuid, dirname, listversion, pomar, timestamp) 
		values (?, ?, ?, ?, ?, ?, ?, datetime())
		""", (values['filename'], values['size'], values['hash'], 
			values['uuid'], values['dirname'], values['listversion'], sanitize_pomar(pomar))
		)

		if commit:
			self.db.commit()

	def updatePomarPath(self, pomar, path):
		"""Updates toc with pomar and its pathname location on the disk."""

		self.cursor.execute("""
		insert or ignore into locations (pomar, pathname) 
		values (?, ?)
		""", (sanitize_pomar(pomar), path)
		)
		
		self.db.commit()

	def pathFor(self, hash, pomar='/'):
		"""Returns the fullpath and size of a local file given a hash and pomar."""

		pomar_path = self.pathForPomar(pomar)

		if pomar_path is None:
			return None
		
		self.cursor.execute("""
		select filename, dirname, size, max(listversion) from toc where uuid=? and hash=? and pomar=?
		""", (my_uuid, hash, sanitize_pomar(pomar), )
		)

		filepath = self.cursor.fetchone()
		if filepath is not None:
			return (os.path.expanduser(os.path.join(pomar_path, filepath[1], filepath[0])), filepath[2])

		return None

		

	def pathForPomar(self, pomar):
		"""Returns the pathname for a local pomar."""

		self.cursor.execute("""
		select pathname from locations where pomar=?
		""", (sanitize_pomar(pomar), )
		)

		val = self.cursor.fetchone()

		if val is not None:
			return val[0]

		return None


def sanitize_pomar(pomar):
	"""Makes sure a pomar is always named like '/some_pomar/' """
	if pomar == '':
		return '/'

	if pomar[0] != '/':
		pomar = '/'+pomar
	if pomar[len(pomar)-1] != '/':
		pomar = pomar+'/'

	return pomar
			

class Resolver():
	"""The Resolver class resolves Pomares-IDs into peer urls."""

	def __init__(self, resolv_filepath=config.uuid_file):
		if os.path.exists(resolv_filepath):
			self.db = sqlite3.connect(resolv_filepath)
			self.cursor = self.db.cursor()
		else:
			self.db = sqlite3.connect(resolv_filepath)
			self.cursor = self.db.cursor()
			self.cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS "uuid" (
			    "id" TEXT NOT NULL PRIMARY KEY,
			    "url" TEXT,
			    "timestamp" DATETIME NOT NULL,
			    "authkey" TEXT
			)
			"""
			)
			self.db.commit()
			log.log('created uuid database: %s' % resolv_filepath)

	def resolve(self, pomares_id):
		"""Returns a url for a pomares_id, None if not found."""

		self.cursor.execute("""
		select url,timestamp from uuid where id = ?
		""", (pomares_id,))

		val = self.cursor.fetchone()

		if val is not None:
			return val[0]
		
		return None



	def update(self, pomares_id, url):
		"""Updates a pomares_id with its url."""

		self.cursor.execute("""
		insert or replace into uuid (id, url, timestamp) values (?, ?, datetime())
		""", (pomares_id, url))

		self.db.commit()

	def __del__(self):
		self.db.close()


