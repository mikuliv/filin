import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertTrue(report('benchmark_registry_resolved.json')['benchmark_discovery_completed'])

if __name__ == '__main__': unittest.main()

