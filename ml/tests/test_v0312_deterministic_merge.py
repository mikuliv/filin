import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        rows=prediction('v039')['records']; keys=[(x['benchmark_id'],x['run_id'],x['immutable_row_id']) for x in rows]
        self.assertEqual(keys,sorted(keys))

if __name__ == '__main__': unittest.main()

