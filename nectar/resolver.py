"""The resolver module resolves Pomares-IDs into peer urls."""
import db

initialise = """
			CREATE TABLE IF NOT EXISTS "uuid" (
			    "id" TEXT NOT NULL PRIMARY KEY,
			    "url" TEXT,
			    "timestamp" DATETIME NOT NULL,
			    "authkey" TEXT
			)
			"""
database = None

def set_db(db_name):
	"""Sets sqlite database"""
	global database
	database = db.get_db(db_name)


def resolve(pomares_id):
	"""Returns a url for a pomares_id, None if not found."""

	results = database.select("""
	select url,timestamp from uuid where id = ?
	""", (pomares_id,))

	for res in results:
		return res[0]

	return None


def update(pomares_id, url):
	"""Updates a pomares_id with its url."""

	database.execute("""
	insert or replace into uuid (id, url, timestamp) values (?, ?, datetime())
	""", (pomares_id, url))


