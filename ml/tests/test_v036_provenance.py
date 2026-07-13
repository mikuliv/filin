import unittest
from ml.tests.v036_test_utils import load
class ProvenanceTests(unittest.TestCase):
 def test_run_ids_and_seeds_are_unique(self):
  runs=load('lab/campaigns/v0_3_6_blind_holdout.yaml')['runs'];self.assertEqual(len({r['run_id'] for r in runs}),12);self.assertEqual(len({r['random_seed'] for r in runs}),12)
