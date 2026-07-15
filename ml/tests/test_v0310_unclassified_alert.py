import unittest
from v0310_support import ROOT
class TestUnclassified(unittest.TestCase):
 def test_state_declared(self):self.assertIn('alert_emitted:unclassified',(ROOT/'ml/decision/v0310_minimal_promotion.py').read_text(encoding='utf8'))

