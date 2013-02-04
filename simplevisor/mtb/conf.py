"""
Configuration utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""
import re
from subprocess import Popen, PIPE

from mtb.modules import json
from mtb import PY2, PY3


def _normalize_bool(tree):
    """ Normalize boolean in the dict. """
    for key, value in tree.items():
        if type(value) == dict:
            _normalize_bool(value)
        elif type(value) in [str, unicode]:
            if value.lower() == "true":
                tree[key] = True
            elif value.lower() == "false":
                tree[key] = False


def read_apache_config(path):
    """
    Read Apache style config files.
    """
    if path is None:
        return None
    cmd = "perl -e 'use Config::General qw(ParseConfig);" + \
          "use JSON qw(to_json);print(to_json({ParseConfig(" + \
          "-ConfigFile => $ARGV[0], -InterPolateVars => 1)}))' %s" % (path, )
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate()
    if err:
        raise ValueError(str(err).strip())
    data = json.loads(out)
    _normalize_bool(data)
    return data


def unify_keys(dictionary):
    """
    Unify dictionary's keys, if they are unicode transform them to strings.
    This is for interoperability with old versions of Python.
    """
    if type(dictionary) is not dict:
        return dictionary
    for element in dictionary:
        if PY2 and type(element) is not str:
            value = dictionary.pop(element)
            dictionary[str(element)] = value
        elif PY3 and type(element) is bytes:
            value = dictionary.pop(element)
            dictionary[element.decode()] = value
        tmp = dictionary.get(element)
        if type(tmp) is dict:
            unify_keys(tmp)
    return dictionary


_EXPLOSION_RE = re.compile("^(\w+)-(.+)$")


def _explode_dict(given):
    """ Explode all the keys having a "-". """
    for key in given.keys():
        match = _EXPLOSION_RE.match(key)
        if match:
            if match.group(1) in given:
                given[match.group(1)].update(
                    {match.group(2): given.pop(key)})
            else:
                given[match.group(1)] = {
                    match.group(2): given.pop(key)}
    for item in given.values():
        if type(item) == dict:
            _explode_dict(item)


def _tree_dictify(given):
    """ TreeDict-ify it. """
    for key, item in given.items():
        if type(item) == dict:
            _tree_dictify(item)
            given[key] = TreeDict(item)


class TreeDict(object):
    """ Exploded dict. """

    def __init__(self, _dict=None):
        if _dict is None:
            self._dict = dict()
        else:
            self._dict = _dict
            _explode_dict(self._dict)
            _tree_dictify(self._dict)

    def __contains__(self, key):
        return self._dict.__contains__(key)

    def __getitem__(self, key):
        match = _EXPLOSION_RE.match(key)
        if match is None or match.group(1) not in self._dict:
            return self._dict[key]
        value = self._dict[match.group(1)]
        if type(value) is dict:
            return TreeDict(value)[match.group(2)]
        elif type(value) is TreeDict:
            return value[match.group(2)]
        raise KeyError("key not present: %s" % (key, ))

    def get(self, key, default=None):
        """
        Return the value pointed by the given key,
        it the item is not found it returns the default value.
        If default is not provided it will return None.
        """
        match = _EXPLOSION_RE.match(key)
        if match is None:
            return self._dict.get(key, default)
        elif match.group(1) not in self._dict:
            return default
        # match.group(1) in self._dict
        value = self._dict[match.group(1)]
        if type(value) is dict:
            return TreeDict(value).get(match.group(2), default)
        elif type(value) is TreeDict:
            return value.get(match.group(2), default)
        return default

    def pop(self, key, default=None):
        """
        Remove and return the value pointed by the given key,
        it the item is not found it returns the default value.
        If default is not provided it will return None.
        """
        match = _EXPLOSION_RE.match(key)
        if match is None:
            return self._dict.pop(key, default)
        elif match.group(1) not in self._dict:
            return default
        # match.group(1) in self._dict
        value = self._dict.pop(match.group(1), default)
        if type(value) is dict:
            return TreeDict(value).pop(match.group(2), default)
        elif type(value) is TreeDict:
            return value.pop(match.group(2), default)
        return default

    def __setitem__(self, key, val):
        match = _EXPLOSION_RE.match(key)
        if match is None:
            self._dict[key] = val
        else:
            if match.group(1) not in self._dict:
                self._dict[match.group(1)] = TreeDict()
            sub_value = self._dict[match.group(1)]
            sub_value[match.group(2)] = val

    def setdefault(self, key, default=None):
        """
        Set the item identified by key to default value,
        if default is not provided the item will be set to None.
        """
        match = _EXPLOSION_RE.match(key)
        if match is None:
            return self._dict.setdefault(key, default)
        else:
            val = self._dict.setdefault(match.group(1), TreeDict())
            val.setdefault(match.group(2), default)

    def keys(self):
        """
        Return the set of keys.
        """
        return self._dict.keys()

    def items(self):
        """
        Return the set of items.
        """
        return self._dict.items()

    def update(self, *args, **kwargs):
        """
        Update TreeDict with given values.
        """
        return self._dict.update(*args, **kwargs)

    def copy(self):
        """ Return a copy of it. """
        return TreeDict(self._dict)

    def __repr__(self):
        return "%s" % (self._dict, )
