import unittest,yaml,tempfile
from v037_support import ROOT
class TestCandidateFreeze(unittest.TestCase):
 def test_manifest_contract_is_declared_in_runner(self):
  text=(ROOT/'ml/experiments/v0_3_7/run_nested_model_selection.py').read_text(encoding='utf8');self.assertIn('candidate_frozen_before_validation',text);self.assertIn('prohibit_refit_on_validation',text)
