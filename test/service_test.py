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
from simplevisor.service import Service

from mtb.proc import which

import unittest

OK = True
FAIL = False
CREATION_COMBINATIONS = [
    (FAIL, {"name": "foo", }),
    (FAIL, {"name": "foo", "foo": "bar", }),
    (OK, {"name": "foo", "control": "foo", }),
    (OK, {"name": "foo", "control": "foo", "expected": "stopped", }),
    (FAIL, {"name": "foo", "control": "foo", "start": "foo", }),
    (FAIL, {"name": "foo", "control": "foo", "daemon": "pid", }),
    (FAIL, {"name": "foo", "daemon": "pid", }),
    (FAIL, {"name": "foo", "control": "foo", "pattern": "pattern", }),
    (FAIL, {"name": "foo", "start": "start", "pattern": "pattern",
            "stop": "stop", "status": "status", }),
    (OK, {"name": "foo", "start": "start",
          "stop": "stop", "status": "status", }),
]


class ServiceTest(unittest.TestCase):
    """ Test Service module. """

    def test_creation(self):
        """ Test service creation. """
        print("running service creation tests")
        for (shouldpass, options) in CREATION_COMBINATIONS:
            if shouldpass:
                Service(**options)
                continue
            else:
                self.assertRaises(Exception, Service, **options)
        print("...service creation ok")

    def test_daemon_option(self):
        """ Test daemon option. """
        print("running service daemon option test")
        pidfile = "/path/to/pid.pid"
        start = "start command"
        service = Service(
            "foo",
            daemon=pidfile,
            start=start,
            stop="stop command",
            status="status command")
        common = "%s --pidfile %s" % (which("simplevisor-loop"), pidfile, )
        self.assertEqual(
            "%s -c 1 --daemon %s" % (common, start),
            service._opts["start"])
        self.assertEqual(
            "%s --quit" % (common, ),
            service._opts["stop"])
        self.assertEqual(
            "%s --status" % (common, ),
            service._opts["status"])
        print("...service daemon option ok")

if __name__ == "__main__":
    unittest.main()
