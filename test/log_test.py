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
import sys
import unittest
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

import simplevisor.mtb.log as log
from simplevisor.mtb.test import parametrized


OK = True
FAIL = False

LOG_OPERATIONS = "debug info warning error critical".split()

TEST_DIR = os.path.abspath("test_tmp")


def capture(func, *args, **kwargs):
    """ Capture stdout. """
    # setup the environment
    b_out = sys.stdout
    b_err = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = sys.stdout
    func(*args, **kwargs)
    out = sys.stdout.getvalue()
    sys.stdout.close()
    sys.stdout = b_out
    sys.stderr = b_err
    return out


class LogTest(unittest.TestCase):
    """ Test :py:mod:`mtb.log` utilities module. """

    def setUp(self):
        """ Setup the test environment for the log test. """
        # remove the test folder
        shutil.rmtree(TEST_DIR, True)
        # and create it again
        try:
            os.mkdir(TEST_DIR)
        except OSError:
            pass

    def tearDown(self):
        """ Restore the test environment and delete the test folder. """
        shutil.rmtree(TEST_DIR, True)

    @parametrized("log_n log_s".split(), log.LOG_SYSTEM.items())
    def test_init(self, log_n, log_s):
        """ Test log system creation. """
        print("running log system creation for %s"
              % (log_n,))
        log_s("foo")
        log.get_log(log_n)
        print("...test log system creation ok")

    @parametrized("log_n log_s".split(), log.LOG_SYSTEM.items())
    def test_log_operations(self, log_n, log_s):
        """ Test log system operations. """
        print("running log operations checking for %s"
              % (log_n,))
        log_system = log_s("foo")
        for operation in LOG_OPERATIONS:
            capture(getattr(log_system, operation), "foo")
        print("...test log operations checking ok")

if __name__ == "__main__":
    unittest.main()
