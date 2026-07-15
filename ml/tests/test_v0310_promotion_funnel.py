import unittest
from v0310_support import ROOT
class TestFunnel(unittest.TestCase):
 def test_unresolved_reasons(self):self.assertIn('unresolved_reason_counts',(ROOT/'ml/analysis/v0310_promotion_funnel.py').read_text(encoding='utf8'))

