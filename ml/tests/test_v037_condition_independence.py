import unittest,yaml
from v037_support import ROOT
from v037_condition_independence_audit import audit
class TestConditionIndependence(unittest.TestCase):
 def test_missing_runtime_evidence_is_not_reported_as_passed(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_7_training.yaml').read_text(encoding='utf8'));result=audit(c)
  self.assertEqual(result['status'],'not_executed');self.assertFalse(result['v037_condition_independence_valid'])
