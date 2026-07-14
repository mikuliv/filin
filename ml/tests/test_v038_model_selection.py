import unittest
from v038_support import ROOT
class TestModelSelection(unittest.TestCase):
 def test_matrix_fixed(self):
  text=(ROOT/'ml/experiments/v0_3_8/run_nested_model_selection.py').read_text(encoding='utf8');self.assertIn('itertools.product(PROFILES, GATES, SUBTYPES)',text);self.assertIn('[:3]',text)
