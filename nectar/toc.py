"""The Table of Contents module.
It keeps track of the history and locations of all files and peers."""

import config
import os
import log
import db

initialise ="""
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
			CREATE TABLE IF NOT EXISTS "locations" (
			    "pomar" TEXT NOT NULL,
			    "pathname" TEXT NOT NULL,
			    PRIMARY KEY (pomar, pathname)
			)
			"""
database = None

def set_db(db_name):
	"""Sets sqlite database"""
	global database
	database = db.get_db(db_name)


def lastVersionFor(pomares_id, pomar='/'):
	"""Returns the latest listversion for a pomares_id."""

	results = database.select("""
	select max(listversion) from toc where uuid=? and pomar=?
	""", (pomares_id, sanitize_pomar(pomar))
	)

	for res in results:
		return res[0]

	return None


def lastUpdates(pomar='/', all_rows=False):
	"""Returns a list of pomares-IDs and latest listversions."""

	results = database.select("""
	select uuid,listversion from toc where pomar=? group by uuid having max(listversion)
	""", (sanitize_pomar(pomar),)
	)

	if all_rows:
		return [row for row in results]

	return results


def listVersion(pomares_id, from_to, pomar='/', all_rows=False):
	"""Returns a list of files for a pomares_id between versions in from_to tuple"""
	
	results = database.select("""
	select filename, size, hash, uuid, dirname, listversion from toc 
	where uuid=? and pomar=? and listversion between ? and ?
	""", (pomares_id, sanitize_pomar(pomar), from_to[0], from_to[1])
	)

	if all_rows:
		return [row for in results]
	
	return results

def whoHas(hash, orderByTime=True):
	"""Returns the uuids with respective filenames, filesizes, dirnames and pomar for hash."""

	order_string=""

	if orderByTime:
		order_string = "order by timestamp desc"

	results = database.select("""
	select uuid, filename, size, dirname, pomar from toc where hash=? 
	group by pomar, uuid having max(listversion) %s
	""" % order_string, (hash,) 
	)

	return results

def update(values, pomar='/'):
	"""Updates toc with values for dict {filename, size, hash, uuid, dirname, listversion, pomar}."""

	database.execute("""
	insert or ignore into toc (filename, size, hash, uuid, dirname, listversion, pomar, timestamp) 
	values (?, ?, ?, ?, ?, ?, ?, datetime())
	""", (values['filename'], values['size'], values['hash'], 
		values['uuid'], values['dirname'], values['listversion'], sanitize_pomar(pomar))
	)

def updatePomarPath(pomar, path):
	"""Updates toc with pomar and its pathname location on the disk."""

	database.execute("""
	insert or ignore into locations (pomar, pathname) 
	values (?, ?)
	""", (sanitize_pomar(pomar), path)
	)
	
def pathFor(hash, pomar='/'):
	"""Returns the fullpath and size of a local file given a hash and pomar."""

	pomar_path = pathForPomar(pomar)

	if pomar_path is None:
		return None
	
	results = database.select("""
	select filename, dirname, size, max(listversion) from toc where uuid=? and hash=? and pomar=?
	""", (config.my_uuid, hash, sanitize_pomar(pomar), )
	)

	filepath = None
	for res in results:
		filepath = res
		break

	if filepath is not None:
		return (os.path.expanduser(os.path.join(pomar_path, filepath[1], filepath[0])), filepath[2])

	return None

	

def pathForPomar(pomar):
	"""Returns the pathname for a local pomar."""

	results = database.select("""
	select pathname from locations where pomar=?
	""", (sanitize_pomar(pomar), )
	)

	for res in results:
		return res[0]

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
			

