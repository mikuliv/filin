import unittest,yaml
from v037_support import ROOT
class TestPolicyResult(unittest.TestCase):
 def test_shadow_and_backend_are_never_enabled(self):
  text=(ROOT/'ml/experiments/v0_3_7/run_internal_validation.py').read_text(encoding='utf8');self.assertIn("'candidate_ready_for_shadow_mode':False",text);self.assertIn("'sensor_ready_for_backend_integration':False",text)
