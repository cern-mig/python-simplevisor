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

import simplevisor.utils as sutils
from test.utils import parametrized
import os
import shutil
import sys
import unittest

def u_(value):
    if sutils.PY2:
        return unicode(value)
    return value

TEST_DIR = os.path.abspath("test_tmp")
TIMED_PROCESS_SETS_NAMES = "error command timeout result".split()
TIMED_PROCESS_SETS = (
    (None, "sleep 1", 10, (0, ''.encode(), ''.encode())),
    (None, "echo ciao", 10,
     (0, 'ciao\n'.encode(), ''.encode())),
    (None, "test -x /dev/null", 10,
     (1, ''.encode(), ''.encode())),
    (sutils.ProcessTimedout, "sleep 5", 1, None),
    (sutils.ProcessError, "skjghdjskhfgkdf", 5, None),)
UNIFY_KEYS_SETS_NAMES = "error given result".split()
UNIFY_KEYS_SETS = (
    (None, None, None),
    (None, "", ""),
    (None, {'hello': 'world'}, {'hello': 'world'}),
    (None, {u_('hello'): 'world'}, {'hello': 'world'}),
    (None, {u_('hello'): 'world', 'foo': {u_('hello'): 'world'}},
     {'hello': 'world', 'foo': {'hello': 'world'}}),
)


class UtilsTest(unittest.TestCase):
    """ Test utilities module. """

    def setUp(self):
        """ Setup the test environment. """
        shutil.rmtree(TEST_DIR, True)
        try:
            os.mkdir(TEST_DIR)
        except OSError:
            pass

    def tearDown(self):
        """ Restore the test environment. """
        shutil.rmtree(TEST_DIR, True)

    @parametrized(TIMED_PROCESS_SETS_NAMES, TIMED_PROCESS_SETS)
    def test_timed_process(self, error, command, timeout, result):
        """ Test timed_process. """
        print("running timed_process for %s"
              % (command, ))
        got = None
        result_got = None
        try:
            result_got = sutils.timed_process(command.split(), timeout)
        except sutils.ProcessError:
            got = sutils.ProcessError
        except sutils.ProcessTimedout:
            got = sutils.ProcessTimedout
        if got == error:
            if result_got != result:
                raise AssertionError(
                    "command %s was expected to return %s, it returned %s" %
                    (command, result, result_got, ))
        else:
            raise AssertionError(
                "command %s was expected to fail with error: %s" %
                (command, error, ))
        print("...test timed_process ok")

    @parametrized(UNIFY_KEYS_SETS_NAMES, UNIFY_KEYS_SETS)
    def test_unify_keys(self, error, given, result):
        """ Test unify kes. """
        print("running unify keys for %s" % (given, ))
        got = None
        result_got = None
        try:
            result_got = sutils.unify_keys(given)
        except:
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

    def some_function(**kwargs):
        """ Example. """
        pass

    def test_unicode_keywords_function(self):
        """ Test unicode keywords function. """
        error = None
        unicode_dict = {u'hello': 'world'}
        try:
            some_function(**unicode_dict)
        except:
            error = sys.exc_info()[1]
        if type(error) is TypeError:
            sutils.unify_keys(unicode_dict)
            some_function(**unicode_dict)


if __name__ == "__main__":
    unittest.main()
