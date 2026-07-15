import unittest
from v039_support import ROOT
class TestFreeze(unittest.TestCase):
 def test_manifest_contract_in_source(self):
  t=(ROOT/'ml/experiments/v0_3_9/select_decision_policy.py').read_text(encoding='utf8');self.assertIn('candidate_frozen_before_validation_collection',t);self.assertIn('model_trained_on_v038_data',t)
