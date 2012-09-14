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
from simplevisor.errors import ConfigurationError
from simplevisor.supervisor import Supervisor
import unittest

OK = True
FAIL = False

class SupervisorTest(unittest.TestCase):

    def setUp(self):
        """ Setup the test environment. """
        pass
    
    def tearDown(self):
        """ Restore the test environment. """
        pass

    def test_init(self):
        """ Test supervisor init. """
        print("running supervisor init test")
        try:
            Supervisor()
            self.assert_(False, "Supervisor() should raise ConfigurationError")
        except ConfigurationError:
            pass
        print("...supervisor init ok")
    
if __name__ == "__main__":
    unittest.main()  