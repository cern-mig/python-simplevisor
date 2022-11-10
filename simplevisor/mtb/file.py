"""
File utilities for :py:mod:`mtb` module.


Copyright (C) CERN 2013-2021
"""
import io
import os
import stat

from mtb import PY2, PY3


# File helper
def is_regular_file(element):
    """
    Return True if the given element is a regular file.

    It accepts input as :py:mod:`file`, :py:mod:`str` or :py:mod:`int`.
    """
    if PY2 and type(element) is file:
        fstat = os.fstat(element.fileno())
    elif PY3 and isinstance(element, io.TextIOWrapper):
        fstat = os.fstat(element.fileno())
    elif type(element) is str:
        fstat = os.stat(element)
    elif type(element) is int:
        fstat = os.fstat(element)
    else:
        raise ValueError("is_regular_file accepts: file, str or int")
    return stat.S_ISREG(fstat.st_mode)
