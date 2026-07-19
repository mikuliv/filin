import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(len(report('v0310_input_lock.json')['input_lock_sha256']),64)

if __name__ == '__main__': unittest.main()

