import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertEqual([x['feature_count'] for x in compatibility()[-2:]],[51,51])

if __name__ == '__main__': unittest.main()

