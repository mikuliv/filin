import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_groups(self): self.assertEqual(set(json.loads((R/'ml/reports/v0_3_5/per_group_metrics.json').read_text())),{'mixed','hard_negative','degraded','tls_proxy'})
