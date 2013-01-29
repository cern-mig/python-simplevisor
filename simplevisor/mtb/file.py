"""
File utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""
import os
import stat


#### File helper
def is_regular_file(element):
    """
    Return True if the given element is a regular file.

    It accepts input as :py:mod:`file`, :py:mod:`str` or :py:mod:`int`.
    """
    if type(element) is file:
        fstat = os.fstat(element.fileno())
    elif type(element) is str:
        fstat = os.stat(element)
    elif type(element) is int:
        fstat = os.fstat(element)
    else:
        raise ValueError(
            "is_regular_file accept: file, str or file descriptor no.")
    return stat.S_ISREG(fstat.st_mode)
