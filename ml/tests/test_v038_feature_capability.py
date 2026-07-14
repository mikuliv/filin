import unittest
from v0_6_feature_capability_audit import audit
class TestFeatureCapability(unittest.TestCase):
 def test_all_supported(self):
  result=audit();self.assertTrue(result['v038_feature_capability_valid']);self.assertEqual(result['evidence_feature_count'],60);self.assertFalse(result['unsupported_features'])
