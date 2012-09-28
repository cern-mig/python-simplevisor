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


Copyright (C) 2012 CERN
"""

import simplevisor.utils as sutils
from utils import parametrized
import os
import shutil
import time
from threading import Thread
import unittest

TestDir = os.path.abspath("test_tmp")
TimedProcessSetsNames = "error command timeout result".split()
TimedProcessSets = ((None, "sleep 1", 10, (0, ''.encode(), ''.encode())),
                    (None, "echo ciao", 10,
                     (0, 'ciao\n'.encode(), ''.encode())),
                    (None, "test -x /dev/null", 10,
                     (1, ''.encode(), ''.encode())),
                    (sutils.ProcessTimedout, "sleep 5", 1, None),
                    (sutils.ProcessError, "skjghdjskhfgkdf", 5, None),)


class UtilsTest(unittest.TestCase):

    def setUp(self):
        """ Setup the test environment. """
        shutil.rmtree(TestDir, True)
        try:
            os.mkdir(TestDir)
        except:
            pass

    def tearDown(self):
        """ Restore the test environment. """
        shutil.rmtree(TestDir, True)

    @parametrized(TimedProcessSetsNames, TimedProcessSets)
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


if __name__ == "__main__":
    unittest.main()
