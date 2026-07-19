import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        from ml.experiments.v0_3_12.performance_controller import PROFILES
        self.assertLessEqual(max(w*t for w,t in PROFILES.values()),12)

if __name__ == '__main__': unittest.main()

