import unittest
from ml.tests.v036_test_utils import ROOT
class NoFitTests(unittest.TestCase):
 def test_evaluator_has_no_training_calls(self):
  text=(ROOT/'ml/analysis/v036_evaluation.py').read_text(encoding='utf-8');self.assertNotIn('.fit(',text);self.assertNotIn('.partial_fit(',text);self.assertNotIn('GridSearchCV',text)
