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
import sys
import unittest

from simplevisor.mtb.conf import unify_keys
from simplevisor.mtb.string import u_


def some_function(**_):
    """ Example. """
    pass


class StringTest(unittest.TestCase):
    """ Test :py:mod:`mtb.string` utilities module. """
    
    def test_unicode_keywords_function(self):
        """ Test unicode keywords function. """
        error = None
        unicode_dict = {u_('hello'): 'world'}
        try:
            some_function(**unicode_dict)
        except Exception:
            error = sys.exc_info()[1]
        if type(error) is TypeError:
            unify_keys(unicode_dict)
            some_function(**unicode_dict)


if __name__ == "__main__":
    unittest.main()
