import unittest
from ml.tests.v036_test_utils import ROOT
class PreflightTests(unittest.TestCase):
 def test_preflight_does_not_load_model(self):
  text=(ROOT/'lab/holdout/v0_3_6_preflight.py').read_text(encoding='utf-8');self.assertNotIn('joblib',text);self.assertNotIn('.predict(',text)
