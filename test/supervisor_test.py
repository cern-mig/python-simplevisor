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
import simplevisor
from simplevisor.errors import SimplevisorError
from simplevisor.supervisor import Supervisor
from simplevisor.service import Service

#import mtb.log as log
#log.set_log(log.StdOutLog("test", loglevel="debug"))

import copy
import os
import shutil
import time
import unittest

TEST_DIR = os.path.join(os.getcwd(), "test_directory")

T_SVC1_OK = {
    'name': 'svc1',
    'type': 'service',
    'start': 'sleep 101',
    'daemon': os.path.join(TEST_DIR, 'svc1.pid'), }
T_SVC2_OK = {
    'name': 'svc2',
    'type': 'service',
    'expected': 'stopped',
    'start': 'sleep 102',
    'daemon': os.path.join(TEST_DIR, 'svc2.pid'), }
T_SVC3_OK = {
    'name': 'svc3',
    'type': 'service',
    'start': 'sleep 103',
    'daemon': os.path.join(TEST_DIR, 'svc3.pid'), }
T_SUP2_OK = {
    'name': 'sup2',
    'type': 'supervisor',
    'children': {
    'entry': [T_SVC3_OK, ], }}
T_SUP1_OK = {
    'name': 'sup1',
    'children': {
    'entry': [T_SVC1_OK, T_SUP2_OK, T_SVC2_OK], }}

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
        self.path = TEST_DIR
        shutil.rmtree(self.path, ignore_errors=True)
        os.makedirs(self.path)

    def tearDown(self):
        """ Restore the test environment. """
        shutil.rmtree(self.path, ignore_errors=True)

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
            sup1 = Supervisor(**current)
            sup1.start()
            time.sleep(1)
            (check, check_output) = sup1.check()
            self.assertTrue(check, "sup1 check should be successful")
            successful = sup1.supervise()
            self.assertTrue(
                successful, "sup1 supervise should have been successful")
            child1 = sup1.get_child(["svc1"])
            child1.cond_stop(careful=True)
            (child1_status, _, _) = child1.status()
            self.assertNotEqual(child1_status, 0, "svc1 should be stopped")
            successful = sup1.supervise()
            self.assertTrue(
                successful, "sup1 supervise should have been successful")
            (child1_status, _, _) = child1.status()
            self.assertEqual(child1_status, 0, "svc1 should be started")
            sup1.stop()
            time.sleep(1)
        print("...supervisor start ok")
        

if __name__ == "__main__":
    unittest.main()
