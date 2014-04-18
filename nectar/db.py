import gdbm as dbm
import os
from time import time

open_dbs = {}


def get(name, path='', read_only=False, name_fmt=None):
    "Return an open or existing db."

    if (name_fmt is None) and (name in open_dbs):
        return open_dbs[name]

    elif ((name_fmt is not None) and (name_fmt in open_dbs)):
        return open_dbs[name_fmt]

    if os.path.exists(os.path.join(path, name)):
        if read_only:
            db = DB(name, path, mode='r')
        else:
            db = DB(name, path)
        if name_fmt:
            open_dbs[name_fmt] = db
        else:
            open_dbs[name] = db

        return db

    #DB does not exist:
    return None


def new(name, path='', name_fmt=None):
    "Create and return a new db."
    if not os.path.exists(path):
        os.mkdir(path)
    db = DB(name, path)
    if name_fmt:
        open_dbs[name_fmt] = db
    else:
        open_dbs[name] = db

    return db


def delete(name):
    "Close a db."
    if name in open_dbs:
        del open_dbs[name]


def close_old(max=5):
    """Close oldest max number of open dbs"""
    time_sorted = sorted(open_dbs.items(),
                         key=lambda (i): i[1].time) # i[1] is db

    for name, db in time_sorted[:max]:
        print '>>>>> closing', name, db.time
        delete(name)
        

class DB():
    "The DB class."
    def __init__(self, name, path='', mode='c'):
        self.name = name
        self.path = path
        self.mode = mode

        # retry logic when too many files are open
        # e.g.
        # error: (24, 'Too many open files')
        while True:
            try:
                self.db = dbm.open(os.path.join(self.path, self.name), self.mode)
                self.time = time() # open time
                break
            except dbm.error, err:
                if err[0] == 24:
                    close_old()
                else:
                    raise
                    break

    def reload(self):
        self.db.close()
        self.db = dbm.open(os.path.join(self.path, self.name), self.mode)
        self.time = time()

    def __del__(self):
        try:
            self.db.close()
        except AttributeError:
            pass

    def __cmp__(self, y):
        """compare objects by time"""
        if self.time < y.time:
            return -1 
        if self.time == y.time:
            return 0 
        if self.time > y.time:
            return 1 
