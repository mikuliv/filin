import unittest
from v039_support import ROOT
class TestLatency(unittest.TestCase):
 def test_second_window_separate(self):
  t=(ROOT/'ml/experiments/v0_3_9/pipeline.py').read_text(encoding='utf8');self.assertIn('detection_by_second_window',t);self.assertIn('standard_deviation',t)
