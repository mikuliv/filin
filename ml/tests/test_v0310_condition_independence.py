import unittest
from v0310_support import ROOT
from v0310_condition_independence_audit import audit
class TestCondition(unittest.TestCase):
 def test_groups(self):
  r=audit(ROOT/'lab/campaigns/v0_3_10_training.yaml',ROOT/'lab/campaigns/v0_3_10_internal_validation.yaml',ROOT/'ml/reports/v0_3_10/test_condition.json');self.assertTrue(r['v0310_condition_independence_valid'])

