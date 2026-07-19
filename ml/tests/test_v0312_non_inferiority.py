import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertIn('non_inferiority_policy_passed',policy())

if __name__ == '__main__': unittest.main()

