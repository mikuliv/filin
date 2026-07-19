import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertTrue((EXP/'run_v0_3_12.py').exists())

if __name__ == '__main__': unittest.main()

