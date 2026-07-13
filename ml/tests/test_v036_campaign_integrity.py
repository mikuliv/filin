import unittest
from ml.tests.v036_test_utils import load
class IntegrityTests(unittest.TestCase):
 def test_expected_composition(self):
  c=load('lab/campaigns/v0_3_6_blind_holdout.yaml');self.assertEqual(len(c['runs']),12);self.assertEqual(len(c['execution_catalog']['benign']),16);self.assertEqual(12*21,252)
