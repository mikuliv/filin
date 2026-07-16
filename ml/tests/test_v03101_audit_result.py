import unittest
from ml.tests._v03101_support import ROOT
class TestAuditResult(unittest.TestCase):
 def test_runner_defines_negative_status(self):
  t=(ROOT/"ml/audits/v0_3_10_1/run_v0_3_10_1_audit.py").read_text(encoding="utf-8");self.assertIn('"v0310_internal_validation_passed":False',t);self.assertIn('"candidate_ready_for_shadow_mode":False',t)
