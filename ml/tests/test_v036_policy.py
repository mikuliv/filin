import unittest
from ml.tests.v036_test_utils import load
class PolicyTests(unittest.TestCase):
 def test_frozen_thresholds_match_spec(self):
  p=load('ml/experiments/v0_3_6/holdout_evaluation_policy.yaml');self.assertEqual(p['evaluation_policy']['minimum_macro_f1'],.78);self.assertEqual(p['evaluation_policy']['minimum_balanced_accuracy'],.85);self.assertEqual(p['group_policy']['minimum_attack_macro_recall'],.70)
