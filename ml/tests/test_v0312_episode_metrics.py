import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(metric('v0310')['episode']['attack_episode_recall'],1.0)

if __name__ == '__main__': unittest.main()

