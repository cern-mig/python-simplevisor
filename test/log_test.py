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

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import simplevisor.log as slog
from utils import parametrized
import os
import shutil
import sys
import time
import unittest

OK = True
FAIL = False

LOG_OPERATIONS = "debug info warning error critical".split()

TestDir = os.path.abspath("test_tmp")

def capture(callable, *args, **kwargs):
    # setup the environment
    b_out = sys.stdout
    b_err = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = sys.stdout
    callable(*args, **kwargs)
    out = sys.stdout.getvalue()
    sys.stdout.close()
    sys.stdout = b_out
    sys.stderr = b_err
    return out
    
class LogTest(unittest.TestCase):

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

    @parametrized("log_n log_s".split(), slog.LOG_SYSTEM.items())
    def test_init(self, log_n, log_s):
        """ Test log system creation. """
        print("running log system creation for %s"
              % (log_n,))
        l = log_s("foo")
        l2 = slog.get_log(log_n)
        print("...test log system creation ok")
        
    @parametrized("log_n log_s".split(), slog.LOG_SYSTEM.items())
    def test_log_operations(self, log_n, log_s):
        """ Test log system operations. """
        print("running log operations checking for %s"
              % (log_n,))
        l = log_s("foo")
        for operation in LOG_OPERATIONS:
            capture(getattr(l, operation), "foo")
        print("...test log operations checking ok")
        
if __name__ == "__main__":
    unittest.main()  
