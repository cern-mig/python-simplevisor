"""
Validation utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""
import sys


def mutex(container, *options):
    """ Given options must be mutually exclusive. """
    found = None
    for option in options:
        if container.get(option) is None:
            continue
        if found is not None:
            raise ValueError("options %s and %s are mutually exclusive" %
                             (found, option))
        else:
            found = option


def reqall(container, first, *options):
    """ If the first option is present require all the others. """
    if first is not None and container.get(first) is None:
        return
    for option in options:
        if container.get(option) is not None:
            continue
        if first is None:
            raise ValueError("options %s is required" % (option,))
        raise ValueError("option %s requires option %s" % (first, option))


def reqany(container, first, *options):
    """ If the first option is set, at least one of the others is required. """
    if first is not None and container.get(first) is None:
        return
    for option in options:
        if container.get(option) is not None:
            return
    if first is None:
        raise ValueError("one of this option is required: %s" %
                         (", ".join(options)))
    raise ValueError("option %s requires one of: %s" %
                     (first, ", ".join(options)))


def get_int_or_die(value, message=None):
    """
    Return the integer value or die with the error message provided.
    """
    if type(value) == int:
        return value
    try:
        value = int(value)
    except ValueError:
        if message is None:
            raise sys.exc_info()[1]
        else:
            raise ValueError(message)
    return value
