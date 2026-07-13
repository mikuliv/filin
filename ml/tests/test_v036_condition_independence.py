import unittest
from ml.tests.v036_test_utils import ROOT,load
from v036_condition_independence_audit import audit
class ConditionTests(unittest.TestCase):
 def test_conditions_do_not_depend_on_label(self):self.assertTrue(audit(ROOT/'lab/campaigns/v0_3_6_blind_holdout.yaml',ROOT/'lab/holdout/v036_environment_profiles.yaml')['v036_condition_independence_valid'])
 def test_four_profiles(self):self.assertEqual(len(load('lab/holdout/v036_environment_profiles.yaml')['profiles']),4)
