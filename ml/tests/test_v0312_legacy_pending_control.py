import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertFalse(metric('v0310')['legacy_pending_control']['legacy_pending_affects_v0312_pass_fail'])

if __name__ == '__main__': unittest.main()

