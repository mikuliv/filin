import unittest,yaml
from v037_support import ROOT
from v037_condition_independence_audit import audit
class TestConditionIndependence(unittest.TestCase):
 def test_no_label_specific_conditions(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_7_training.yaml').read_text(encoding='utf8'));self.assertTrue(audit(c)['v037_condition_independence_valid'])
