import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertGreaterEqual(metric('v039')['macro_f1'],.75)

if __name__ == '__main__': unittest.main()

