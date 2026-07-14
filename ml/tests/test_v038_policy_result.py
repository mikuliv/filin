import unittest,yaml
from v038_support import ROOT
class TestPolicyResult(unittest.TestCase):
 def test_shadow_always_false(self):
  text=(ROOT/'ml/experiments/v0_3_8/run_internal_validation.py').read_text(encoding='utf8');self.assertIn('candidate_ready_for_shadow_mode": False',text);self.assertIn('candidate_ready_for_v039_regression',text)
