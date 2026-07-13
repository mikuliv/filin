import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_support(self): self.assertEqual(json.loads((R/'ml/reports/v0_3_5/candidate_metrics.json').read_text())['macro_f1'],1.0)
