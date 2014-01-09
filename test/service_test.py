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

Copyright (C) 2013-2014 CERN
"""
from simplevisor.errors import ServiceError
from simplevisor.service import Service

from mtb.proc import which
import mtb.log
mtb.log.setup_log("simplevisor", "stdout", "info")

from copy import deepcopy
import os
import shutil
import unittest

TEST_DIR = os.path.join(os.getcwd(), "test_directory")

OK = True
FAIL = False
T_SVC1_OK = {
    'name': 'svc1',
    'start': 'sleep 101',
    'daemon': os.path.join(TEST_DIR, 'svc1.pid'), }
T_SVC2_OK = {
    'name': 'svc2',
    'start': 'sleep 102',
    'daemon': os.path.join(TEST_DIR, 'svc2.pid'), }
T_SVC3_FAIL = {
    'name': 'svc3',
    'start': 'sleeeeep 103',
    'status': 'sleeep',
    'stop': 'echo hello'}
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
    (OK, deepcopy(T_SVC1_OK)),
    (OK, deepcopy(T_SVC2_OK)),
    (OK, deepcopy(T_SVC3_FAIL))
]


class ServiceTest(unittest.TestCase):
    """ Test Service module. """

    def setUp(self):
        """ Setup the test environment. """
        self.path = TEST_DIR
        shutil.rmtree(self.path, ignore_errors=True)
        os.makedirs(self.path)

    def tearDown(self):
        """ Restore the test environment. """
        shutil.rmtree(self.path, ignore_errors=True)

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

    def test_start_fail(self):
        """
        Test service start fail.
        """
        print("running service start failure expected")
        opts = deepcopy(T_SVC3_FAIL)
        svc = Service(**opts)
        self.assertRaises(ServiceError, svc.cond_start)
        self.assertRaises(ServiceError, svc.cond_start, careful=True)
        print("...service start failure expected ok")

    def test_start_stop(self):
        """
        Test service start - stop.
        """
        print("running service start - stop tests")
        for opts in [deepcopy(T_SVC1_OK), deepcopy(T_SVC2_OK), ]:
            svc = Service(**opts)
            svc.cond_start(careful=True)
            self.assertEquals(
                0, svc.status()[0],
                "%s should be started" % (svc.name,))
            self.assertTrue(
                svc.check()[0],
                "check should have returned true for %s" % (svc.name, ))
            svc.cond_stop(careful=True)
            self.assertEquals(
                3, svc.status()[0],
                "%s should be stopped" % (svc.name,))
            self.assertFalse(
                svc.check()[0],
                "check should have returned true for %s" % (svc.name, ))
        print("...service start-stop ok")

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
