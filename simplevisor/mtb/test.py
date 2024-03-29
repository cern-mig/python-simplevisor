"""
Test utilities for :py:mod:`mtb` module.


Copyright (C) CERN 2013-2021
"""


def parametrized(arg_list, values):
    """ Outer function. """
    def parametrized(function):
        """ Middle function. """
        def parametrized(*args, **kwargs):
            """ Inner function. """
            __name__ = function.__name__
            for value_set in values:
                arg = dict(zip(arg_list, value_set))
                function(*args, **arg)
        return parametrized
    return parametrized
