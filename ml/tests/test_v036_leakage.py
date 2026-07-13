import unittest
from ml.tests.v036_test_utils import load
from v036_leakage_audit import audit
class LeakageTests(unittest.TestCase):
 def test_candidate_features_have_no_metadata(self):self.assertTrue(audit(load('ml/experiments/v0_3_4/frozen_candidate_manifest.yaml')['ordered_feature_list'])['v036_leakage_valid'])
