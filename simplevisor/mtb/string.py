"""
Print utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""
from simplevisor.mtb import PY2


def u_(value):
    """
    Unicode it independently from Python version.
    """
    if PY2:
        return unicode(value)
    return value
