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

Copyright (C) 2013-2016 CERN
"""
from simplevisor.supervisor import Supervisor

import copy
import mtb.log
import os
import shutil
import tempfile
import time
import unittest

TEST_LOGNAME = os.path.basename(__file__)
TEST_DIR = tempfile.mkdtemp(prefix='simplevisor-supervisor')
TEST_LOG = os.path.join(TEST_DIR, "log")

T_SVC1_OK = {
    'name': 'svc1',
    'type': 'service',
    'start': 'sleep 101',
    'daemon': os.path.join(TEST_DIR, 'svc1.pid'),
}
T_SVC2_OK = {
    'name': 'svc2',
    'type': 'service',
    'expected': 'stopped',
    'start': 'sleep 102',
    'daemon': os.path.join(TEST_DIR, 'svc2.pid'),
}
T_SVC3_OK = {
    'name': 'svc3',
    'type': 'service',
    'start': 'sleep 103',
    'daemon': os.path.join(TEST_DIR, 'svc3.pid'),
}
T_SUP2_OK = {
    'name': 'sup2',
    'type': 'supervisor',
    'children': {
        'entry': [T_SVC3_OK, ],
    },
}
T_SUP1_OK = {
    'name': 'sup1',
    'window': 5,
    'adjustments': 3,
    'children': {
        'entry': [T_SVC1_OK, T_SUP2_OK, T_SVC2_OK],
    },
}

OK = True
FAIL = False
CREATION_COMBINATIONS = [
    (FAIL, dict()),
    (FAIL, {'window': 'hello', }),
    (OK, copy.deepcopy(T_SUP1_OK)),
]


class SupervisorTest(unittest.TestCase):
    """ Test Supervisor module. """

    def setUp(self):
        """ Setup the test environment. """
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        os.makedirs(TEST_DIR)
        handler_options = dict()
        handler_options["filename"] = TEST_LOG
        extra = {"handler_options": handler_options}
        mtb.log.setup_log(TEST_LOGNAME, "file", "info", extra)

    def tearDown(self):
        """ Restore the test environment. """
        # with open(TEST_LOG, "r") as fin:
        #    print fin.read()
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    def test_creation(self):
        """ Test supervisor creation. """
        print("running supervisor creation test")
        for (shouldpass, options) in CREATION_COMBINATIONS:
            if shouldpass:
                Supervisor(**options)
                continue
            else:
                self.assertRaises(Exception, Supervisor, **options)
        print("...supervisor init ok")

    def test_start_supervise_stop(self):
        """ Test supervisor start supervise stop. """
        print("running supervisor start-supervise-stop test")
        for strategy in ['one_for_one', 'rest_for_one', 'one_for_all']:
            print("testing %s strategy" % (strategy, ))
            current = copy.deepcopy(T_SUP1_OK)
            current['children']['entry'][1]['strategy'] = strategy
            current['strategy'] = strategy
            current['logname'] = TEST_LOGNAME
            sup1 = Supervisor(**current)
            sup1.start()
            time.sleep(1)
            (check, check_output) = sup1.check()
            self.assertTrue(
                check, "sup1 check should be successful, got: %s\n%s" %
                (check, check_output))
            successful = sup1.supervise()
            self.assertTrue(
                successful, "sup1 supervise should have been successful")
            print("check supervise output: %s\n%s" % (check, check_output))
            sup1.stop()
            time.sleep(1)
            (check, check_output) = sup1.check()
            self.assertFalse(check, "sup1 should be stopped")
            print("check stop output: %s\n%s" % (check, check_output))
        print("...supervisor start ok")

    def test_start_kill_supervise(self):
        """ Test supervisor start - kill - supervise. """
        print("running supervisor start-kill-supervise test")
        for strategy in ['one_for_one', 'rest_for_one', 'one_for_all']:
            print("testing %s strategy" % (strategy, ))
            current = copy.deepcopy(T_SUP1_OK)
            current['children']['entry'][1]['strategy'] = strategy
            current['strategy'] = strategy
            current['logname'] = TEST_LOGNAME
            sup1 = Supervisor(**current)
            sup1.start()
            time.sleep(1)
            (check, check_output) = sup1.check()
            self.assertTrue(check, "sup1 check should be successful")
            successful = sup1.supervise()
            self.assertTrue(
                successful, "sup1 supervise should have been successful")

            for child_path in [
                    [current['children']['entry'][0]['name'], ],
                    [current['children']['entry'][1]['name'],
                     current['children']['entry'][1]['children']
                     ['entry'][0]['name'], ], ]:
                child = sup1.get_child(child_path)
                child.cond_stop(careful=True)
                (child_status, _, _) = child.status()
                self.assertEquals(
                    child_status, 3,
                    "%s should be stopped: %s" % (child.name, child_status))
                successful = sup1.supervise()
                self.assertTrue(
                    successful, "sup1 supervise should have been successful")
                (check, check_output) = sup1.check()
                self.assertTrue(
                    check, "sup1 check should be successful, got: %s\n%s" %
                    (check, check_output))
                (child_status, _, _) = child.status()
                self.assertEqual(
                    child_status, 0,
                    "%s should be started: %s" % (child.name, child_status))

            for i in range(5):
                self.assertTrue(sup1.supervise())
                self.assertTrue(sup1.check()[0])
            self.assertEqual(0, sup1.adjustments())

            child1 = sup1.get_child(
                [current['children']['entry'][0]['name'], ])
            for i in range(3):
                child1.cond_stop(careful=True)
                self.assertEquals(child1.status()[0], 3)
                self.assertEqual(i, sup1.adjustments(), sup1._cycles)
                self.assertTrue(
                    sup1.supervise(),
                    "supervision failed during cycle nr. %d" % (i, ))
                self.assertEquals(child1.status()[0], 0)
                self.assertEqual(i + 1, sup1.adjustments(), sup1._cycles)
                self.assertFalse(sup1.failed())
            child1.cond_stop(careful=True)
            self.assertEquals(child1.status()[0], 3)
            self.assertFalse(sup1.supervise())
            self.assertTrue(sup1.failed())
            self.assertFalse(sup1.check()[0])

            sup1.stop()
            (check, check_output) = sup1.check()
            self.assertFalse(check, "sup1 should be stopped")
            print("check stop output: %s\n%s" % (check, check_output))
        print("...supervisor start ok")


if __name__ == "__main__":
    unittest.main()
