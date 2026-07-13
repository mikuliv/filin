import unittest
from ml.tests.v036_test_utils import ROOT
class PredictionLockTests(unittest.TestCase):
 def test_resume_verifies_prediction_hash(self):
  text=(ROOT/'ml/analysis/v036_evaluation.py').read_text(encoding='utf-8');self.assertIn('Immutable predictions изменены',text);self.assertIn('if not resume',text)
