import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertTrue(report('historical_references.json')['historical_results_opened_after_new_metrics_freeze'])

if __name__ == '__main__': unittest.main()

