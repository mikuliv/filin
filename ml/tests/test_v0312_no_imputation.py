import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertFalse(read_yaml(EXP/'compatibility_policy.yaml')['allow_imputation'])

if __name__ == '__main__': unittest.main()

