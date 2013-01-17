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
from simplevisor.errors import ConfigurationError
from simplevisor.service import Service
import unittest

OK = True
FAIL = False


class ServiceTest(unittest.TestCase):

    def setUp(self):
        """ Setup the test environment. """
        pass

    def tearDown(self):
        """ Restore the test environment. """
        pass

    def test_init(self):
        """ Test service init. """
        print("running service init test")
        try:
            Service("foo")
            self.assert_(False, "Service(\"foo\") should fail because "
                         "it does not provide a control or start parameter")
        except ConfigurationError:
            pass
        
        pidfile = "/path/to/pid.pid"
        start = "start command"
        service = Service("foo",
                          daemon=pidfile,
                          start=start)
        self.assertEqual(
            "/usr/bin/simplevisor-loop -c 1"
            "--pidfile %s --daemon %s" % (pidfile, start),
            service._opts["start"])
        self.assertEqual(
            "/usr/bin/simplevisor-loop --pidfile %s --quit" % (pidfile, ),
            service._opts["stop"])
        self.assertEqual(
            "/usr/bin/simplevisor-loop --pidfile %s --status" % (pidfile, ),
            service._opts["status"])
        print("...service init ok")

if __name__ == "__main__":
    unittest.main()
