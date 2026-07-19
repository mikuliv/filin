import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertTrue(all(x['absolute_rows_preserved'] for x in report('paired_comparison.json')['benchmarks']))

if __name__ == '__main__': unittest.main()

