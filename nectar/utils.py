from os.path import abspath, commonprefix, relpath
import logging

LOG_FMT = ('%(levelname)s %(name)s'
           '.%(funcName)s:%(lineno)s %(asctime)s:%(message)s')
logging.basicConfig(level=logging.DEBUG,
                    format=LOG_FMT)
logger = logging.getLogger(__name__)


def path_valid(local_path, requested_path):
    """checks if requested_path is included in local_path
    returns comparison and common path"""

    common = commonprefix((abspath(requested_path), local_path))

    return relpath(common, local_path) == '.', common


class PathNotValidException(Exception):
    pass
