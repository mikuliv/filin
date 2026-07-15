import unittest
from v0310_support import ROOT
class TestLatency(unittest.TestCase):
 def test_windows(self):self.assertIn('detection_by_second_window',(ROOT/'ml/experiments/v0_3_10/pipeline.py').read_text(encoding='utf8'))

