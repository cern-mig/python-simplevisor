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
from simplevisor.Simplevisor import Simplevisor
import unittest

OK = True
FAIL = False
CREATION_COMBS = [
    (OK, dict()),
]


class SimplevisorTest(unittest.TestCase):
    """ Test Simplevisor module. """

    def test_init(self):
        """ Test Simplevisor init. """
        print("running Simplevisor init test")
        for (shouldpass, options) in CREATION_COMBS:
            if shouldpass:
                Simplevisor(**options)
                continue
            else:
                self.assertRaises(Exception, Simplevisor, **options)
        print("...Simplevisor init ok")

if __name__ == "__main__":
    unittest.main()
