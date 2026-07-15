import unittest
from v0310_support import ROOT
class TestVariants(unittest.TestCase):
 def test_sixteen(self):self.assertIn('zero_recall_benign_variants',(ROOT/'ml/experiments/v0_3_10/run_internal_validation.py').read_text(encoding='utf8'))

