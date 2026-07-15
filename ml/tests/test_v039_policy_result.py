import unittest
from v039_support import ROOT
class TestPolicy(unittest.TestCase):
 def test_shadow_backend_false(self):
  t=(ROOT/'ml/experiments/v0_3_9/run_internal_validation.py').read_text(encoding='utf8');self.assertIn('"candidate_ready_for_shadow_mode":False',t);self.assertIn('"sensor_ready_for_backend_integration":False',t)
