import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_variants(self): self.assertTrue(all(x['benign_recall']==1 for x in json.loads((R/'ml/reports/v0_3_5/benign_variant_metrics.json').read_text()).values()))
