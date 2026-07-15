import unittest
from v0310_support import ROOT
class TestPolicy(unittest.TestCase):
 def test_safety_flags(self):
  t=(ROOT/'ml/experiments/v0_3_10/run_internal_validation.py').read_text(encoding='utf8');self.assertIn('candidate_ready_for_shadow_mode',t);self.assertIn('model_trained_on_v039_data',t)

