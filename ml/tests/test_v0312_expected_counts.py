import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(sum(x['expected_scored_row_count'] for x in registry()),1248)

if __name__ == '__main__': unittest.main()

