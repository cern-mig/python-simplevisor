"""
Errors used in the simplevisor module.


Copyright (C) 2013 CERN
"""


class LogSystemNotSupported(Exception):
    """ Raised when a log system which is not supported is specified. """


class SimplevisorError(Exception):
    """ Raised when a generic simplevisor error occurs. """
