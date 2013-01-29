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
import os
import shutil
import unittest

from simplevisor.mtb.proc import \
    timed_process, ProcessError, ProcessTimedout
from simplevisor.mtb.test import parametrized


TEST_DIR = os.path.abspath("test_tmp")
TIMED_PROCESS_SETS_NAMES = "error command timeout result".split()
TIMED_PROCESS_SETS = (
    (None, "sleep 1", 10, (0, ''.encode(), ''.encode())),
    (None, "echo ciao", 10,
     (0, 'ciao\n'.encode(), ''.encode())),
    (None, "test -x /dev/null", 10,
     (1, ''.encode(), ''.encode())),
    (ProcessTimedout, "sleep 5", 1, None),
    (ProcessError, "skjghdjskhfgkdf", 5, None),)


class ProcTest(unittest.TestCase):
    """ Test :py:mod:`mtb.proc` utilities module. """

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
            result_got = timed_process(command.split(), timeout)
        except ProcessError:
            got = ProcessError
        except ProcessTimedout:
            got = ProcessTimedout
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


if __name__ == "__main__":
    unittest.main()
