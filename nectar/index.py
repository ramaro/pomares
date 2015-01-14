"tree/file indexes"

from whoosh.fields import SchemaClass, TEXT, ID, NUMERIC, DATETIME
from whoosh import index, qparser
from whoosh.writing import AsyncWriter
import logging
from nectar import config

# each key is an index name
indexes = {}


# generic File schema for imports/exports
class FileSchema(SchemaClass):
    "remote files"
    path = ID(stored=True) # without tree_path
    checksum = ID(stored=True)
    size = NUMERIC(bits=64, signed=False, stored=True)
    tree = ID(stored=True)
    tree_path = ID(stored=True)
    mtime = NUMERIC(stored=True)
    pubkey = ID(stored=True) # only needed for imports


class TreeViewSchema(SchemaClass):
    """user designed tree view.
    set names and paths for imported files
    e.g. set *.jpg as 'jpegs' tree"""
    path = ID(stored=True, unique=True)
    checksum = ID(stored=True)
    tree = ID(stored=True)

def get(index_name):
    try:
        return indexes[index_name]
    except KeyError:
        try:
            ix = index.open_dir(config.index_path, schema=FileSchema, 
                                indexname=index_name)
        except index.EmptyIndexError:
            logging.info("no index \"{}\" found, creating a new one".format(index_name))
            ix = index.create_in(config.index_path, schema=FileSchema,
                                 indexname=index_name)
            indexes[index_name] = ix

        return ix

def get_writer(index_name):
    ix = get(index_name)
    wr = AsyncWriter(ix)
    logging.debug("created index_writer for \"{}\" {}".format(index_name, id(wr)))

    return wr


if __name__ == '__main__':
    schema = ExportedFileSchema()
    tschema = TreeSchema()

    ix = index.create_in("/tmp/indexes", indexname="files", schema=schema)
    w = ix.writer()


    w.add_document(path="/a/1", checksum="abcdef1234",
                   size=123, tree="mytree")
    w.add_document(path="/b/2", checksum="abcdef12345",
                   size=124, tree="mytree")
    w.commit()

    qp = qparser.QueryParser("path", schema=schema)
    q = qp.parse("checksum:abcdef12345")
    #q = qp.parse("tree:mytree")


    with ix.searcher() as s:
        results = s.search(q)
        for r in results:
            print(r)


    ix2 = index.create_in("/tmp/indexes", indexname="trees", schema=tschema)
    w2 = ix2.writer()
    w2.add_document(tree="mytree", path="/a/b/c")
    w2.add_document(tree="mytree", path="/a/b/d")
    w2.commit()


    qp = qparser.QueryParser("path", schema=tschema)
    q = qp.parse("tree:mytree")

    with ix2.searcher() as s:
        results = s.search(q)
        for r in results:
            print(r)
