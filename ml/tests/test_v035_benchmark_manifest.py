import unittest, yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class BenchmarkManifestTests(unittest.TestCase):
 def test_locked_benchmark_declares_actual_size(self):
  m=yaml.safe_load((ROOT/'ml/experiments/v0_3_5/benchmark_manifest.yaml').read_text())
  self.assertEqual((m['expected_runs'],m['expected_rows']),(12,204))
