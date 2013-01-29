"""
Configuration utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""
from simplevisor.mtb.modules import json
from simplevisor.mtb import PY2, PY3
from subprocess import Popen, PIPE


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
        raise ValueError(err)
    data = json.loads(out)
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
