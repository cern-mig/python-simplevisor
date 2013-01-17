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
from simplevisor.errors import SimplevisorError
from simplevisor.supervisor import Supervisor
import unittest

OK = True
FAIL = False
CREATION_COMBINATIONS = [
    (FAIL, dict()),
]

class SupervisorTest(unittest.TestCase):

    def setUp(self):
        """ Setup the test environment. """
        pass

    def tearDown(self):
        """ Restore the test environment. """
        pass

    def test_creation(self):
        """ Test supervisor creation. """
        print("running supervisor creation test")
        for (shouldpass, options) in CREATION_COMBINATIONS:
            if shouldpass:
                service = Supervisor(**options)
                continue
            # else
            try:
                service = Supervisor(**options)
                self.fail(
                    "exception should have been raised for:\nSupervisor(%s)" %
                    string)
            except SimplevisorError:
                pass
        print("...supervisor init ok")

if __name__ == "__main__":
    unittest.main()
