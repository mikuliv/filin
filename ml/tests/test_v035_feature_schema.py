import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_schema(self): self.assertTrue(json.loads((R/'ml/reports/v0_3_5/feature_schema_compatibility.json').read_text())['valid'])
