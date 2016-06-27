"""
Errors used in the simplevisor module.


Copyright (C) 2013-2016 CERN
"""


class SimplevisorError(Exception):
    """ Raised when a generic simplevisor error occurs. """


class ServiceError(Exception):
    """ Raised when a service error occurs. """

    def __init__(self, message, result=None):
        """
        Custom constructor.
        """
        Exception.__init__(self, message)
        self.result = result
