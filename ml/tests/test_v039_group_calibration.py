import unittest
from v039_support import ROOT
class TestCalibration(unittest.TestCase):
 def test_grouped_oof_contract(self):
  t=(ROOT/'ml/experiments/v0_3_9/build_grouped_oof_predictions.py').read_text(encoding='utf8');self.assertIn('oof_base',t);self.assertIn('same_run_prediction_count',t)
