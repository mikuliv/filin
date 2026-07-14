import unittest
from v038_support import ROOT
class TestConformalMetrics(unittest.TestCase):
 def test_required_metrics(self):
  text=(ROOT/'ml/experiments/v0_3_8/pipeline.py').read_text(encoding='utf8');self.assertIn('wrong_only_set_rate',text);self.assertIn('coverage_per_class',text)
