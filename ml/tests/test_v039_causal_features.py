import unittest
from v039_support import ROOT
class TestCausalFeatures(unittest.TestCase):
 def test_history_and_order(self):
  t=(ROOT/'ml/experiments/v0_3_9/pipeline.py').read_text(encoding='utf8');self.assertIn('history_depth=6',t);self.assertNotIn('sort_values(["run_id", "run_sequence"]',t)
