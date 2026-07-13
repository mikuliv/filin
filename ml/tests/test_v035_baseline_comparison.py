import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_gain(self): self.assertGreater(json.loads((R/'ml/reports/v0_3_5/baseline_comparison.json').read_text())['absolute_gain']['macro_f1'],.15)
