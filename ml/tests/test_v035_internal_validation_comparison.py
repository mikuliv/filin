import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_comparison(self): self.assertLessEqual(abs(json.loads((R/'ml/reports/v0_3_5/internal_validation_comparison.json').read_text())['macro_f1']),.20)
