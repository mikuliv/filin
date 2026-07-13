from pathlib import Path
import unittest,yaml
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_size(self): self.assertEqual(yaml.safe_load((R/'ml/experiments/v0_3_5/benchmark_manifest.yaml').read_text())['expected_rows'],204)
