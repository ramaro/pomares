from os.path import abspath, commonprefix, relpath
from os.path import exists as pathexists

def path_valid(local_path, requested_path):
    """checks if requested_path is included in local_path
    returns comparison and common path"""

    common = commonprefix((abspath(requested_path), local_path))

    return relpath(common, local_path) == '.', common


class PathNotValidException(Exception):
    pass

