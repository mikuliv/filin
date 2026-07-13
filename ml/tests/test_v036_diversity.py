import unittest
from ml.tests.v036_test_utils import load
class DiversityTests(unittest.TestCase):
 def test_every_run_has_distinct_seed(self):
  runs=load('lab/campaigns/v0_3_6_blind_holdout.yaml')['runs'];self.assertEqual(len(runs),len({x['random_seed'] for x in runs}))
