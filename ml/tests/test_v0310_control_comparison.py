import unittest
from v0310_support import ROOT
class TestControls(unittest.TestCase):
 def test_five_policies(self):self.assertIn('selected_minimal_policy',(ROOT/'ml/analysis/v0310_control_comparison.py').read_text(encoding='utf8'))

