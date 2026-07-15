import unittest
from v0310_support import ROOT
from v0310_leakage_audit import audit
from network_sensor_v0_6 import CONTROL_PROFILE,ordered_features
class TestLeakage(unittest.TestCase):
 def test_no_metadata(self):self.assertTrue(audit(ordered_features(CONTROL_PROFILE),ROOT/'ml/reports/v0_3_10/test_leak.json')['v0310_leakage_valid'])

