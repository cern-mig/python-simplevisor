"""
Print utilities for :py:mod:`mtb` module.


Copyright (C) CERN 2013-2021
"""
import uuid

from mtb import PY2


def u_(value):
    """
    Unicode it independently from Python version.
    """
    if PY2:
        return unicode(value)
    return value


def get_uuid():
    """ Return a new uuid. """
    return str(uuid.uuid1())
