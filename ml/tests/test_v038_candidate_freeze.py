import unittest
from v038_support import ROOT
class TestCandidateFreeze(unittest.TestCase):
 def test_manifest_contract_in_source(self):
  text=(ROOT/'ml/experiments/v0_3_8/run_nested_model_selection.py').read_text(encoding='utf8');self.assertIn('candidate_frozen_before_validation_collection',text);self.assertIn('model_trained_on_v037_data',text)
