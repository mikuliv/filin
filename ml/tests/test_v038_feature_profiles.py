import unittest
from network_sensor_v0_6 import CONTROL_FEATURES,EVIDENCE_ORDER
class TestFeatureProfiles(unittest.TestCase):
 def test_counts_and_prefix(self):self.assertEqual(len(CONTROL_FEATURES),51);self.assertEqual(len(EVIDENCE_ORDER),60);self.assertEqual(EVIDENCE_ORDER[:51],CONTROL_FEATURES)
