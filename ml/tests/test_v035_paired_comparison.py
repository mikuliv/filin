import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_bootstrap(self): self.assertIn('macro_f1',json.loads((R/'ml/reports/v0_3_5/paired_comparison.json').read_text()))
