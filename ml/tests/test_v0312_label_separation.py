import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertFalse(any('label' in x for x in report('v039_input_lock.json')['rows']))

if __name__ == '__main__': unittest.main()

