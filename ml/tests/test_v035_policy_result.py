import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class PolicyResultTests(unittest.TestCase):
 def test_backend_is_never_enabled(self):
  p=ROOT/'ml/reports/v0_3_5/v0_3_5_policy_result.json'
  self.assertFalse(json.loads(p.read_text())['sensor_ready_for_backend_integration'])
