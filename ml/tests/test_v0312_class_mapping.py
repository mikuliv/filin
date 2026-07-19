import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(read_yaml(EXP/'class_mapping.yaml')['aliases']['beacon_simulation'],'beacon')

if __name__ == '__main__': unittest.main()

