import unittest
from v037_support import *
from v0_5_feature_capability_audit import audit
class TestFeatureCapability(unittest.TestCase):
 def test_all_new_features_supported(self):
  value=audit();self.assertTrue(value['v037_feature_capability_valid']);self.assertEqual(value['supported_feature_count'],35)
