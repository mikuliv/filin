import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertTrue(all('episode' not in x['activity_key_source'] for x in report('v039_input_lock.json')['rows']))

if __name__ == '__main__': unittest.main()

