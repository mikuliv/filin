import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(prediction('v0310')['candidate_id'],'v0311:19176acb401be2d4')

if __name__ == '__main__': unittest.main()

