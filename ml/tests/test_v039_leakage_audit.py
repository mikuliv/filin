import tempfile,unittest
from pathlib import Path
from v039_support import ROOT
from network_sensor_v0_6 import CONTROL_PROFILE,ordered_features
from v039_leakage_audit import audit
class TestLeakage(unittest.TestCase):
 def test_profile_clean(self):
  with tempfile.TemporaryDirectory() as d:self.assertTrue(audit(ordered_features(CONTROL_PROFILE),Path(d)/'a.json')['v039_leakage_valid'])
