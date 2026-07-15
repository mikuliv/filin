import unittest
from v039_support import ROOT
class TestVariantMetrics(unittest.TestCase):
 def test_all_fields(self):
  t=(ROOT/'ml/experiments/v0_3_9/run_internal_validation.py').read_text(encoding='utf8');self.assertIn('mean_benign_support_margin',t);self.assertIn('zero_recall_benign_variants',t)
