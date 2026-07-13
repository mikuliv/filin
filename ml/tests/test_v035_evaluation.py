import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_complete(self): self.assertTrue(json.loads((R/'ml/reports/v0_3_5/v0_3_5_policy_result.json').read_text())['v035_regression_evaluation_completed'])
