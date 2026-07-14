import unittest
from v038_support import ROOT
from v038_condition_independence_audit import audit
class TestConditionIndependence(unittest.TestCase):
 def test_valid(self):self.assertTrue(audit(ROOT/'lab/campaigns/v0_3_8_training.yaml',ROOT/'lab/campaigns/v0_3_8_internal_validation.yaml')['v038_condition_independence_valid'])
