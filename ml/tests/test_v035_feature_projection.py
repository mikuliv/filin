import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_mapping(self): self.assertTrue(json.loads((R/'ml/reports/v0_3_5/benchmark_projection_manifest.json').read_text())['mapping_1_to_1'])
