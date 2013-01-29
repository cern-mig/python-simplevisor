"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Copyright (C) 2013 CERN
"""
import sys
import unittest

from simplevisor.mtb.conf import unify_keys
from simplevisor.mtb.string import u_
from simplevisor.mtb.test import parametrized


UNIFY_KEYS_SETS_NAMES = "error given result".split()
UNIFY_KEYS_SETS = (
    (None, None, None),
    (None, "", ""),
    (None, {'hello': 'world'}, {'hello': 'world'}),
    (None, {u_('hello'): 'world'}, {'hello': 'world'}),
    (None, {u_('hello'): 'world', 'foo': {u_('hello'): 'world'}},
     {'hello': 'world', 'foo': {'hello': 'world'}}),
)


class ConfTest(unittest.TestCase):
    """ Test :py:mod:`mtb.conf` utilities module. """

    @parametrized(UNIFY_KEYS_SETS_NAMES, UNIFY_KEYS_SETS)
    def test_unify_keys(self, error, given, result):
        """ Test unify kes. """
        print("running unify keys for %s" % (given, ))
        got = None
        result_got = None
        try:
            result_got = unify_keys(given)
        except Exception:
            got = type(sys.exc_info()[1])
        if got == error:
            if result_got != result:
                raise AssertionError(
                    "%s was expected to return %s, it returned %s" %
                    (given, result, result_got, ))
        else:
            raise AssertionError(
                "%s was expected to fail with error: %s" %
                (given, error, ))
        print("...test unify keys ok")


if __name__ == "__main__":
    unittest.main()
