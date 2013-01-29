"""
Print utilities for :py:mod:`mtb` module.


Copyright (C) 2013 CERN
"""


def print_nested_list(items, level=0, indent=2):
    """
    Print nested lists elements with indentation.
    """
    for item in items:
        if type(item) == list:
            print_nested_list(item, level + 1, indent)
        else:
            print("%s%s" % (level * indent * " ", item))
