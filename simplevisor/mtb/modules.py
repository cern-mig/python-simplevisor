"""
Extra modules utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""

try:
    import hashlib
    md5_hash = hashlib.md5
except ImportError:
    import md5
    md5_hash = md5.md5

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

try:
    import simplejson as json
except (SyntaxError, ImportError):
    import json
    try:
        getattr(json, "dumps")
    except AttributeError:
        raise ImportError("No available json module.")
