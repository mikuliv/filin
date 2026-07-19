import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertIn('blocked_missing_frozen_features',compatibility()[0]['blocking_reasons'])

if __name__ == '__main__': unittest.main()

