import unittest
from v0310_support import ROOT
class TestSummary(unittest.TestCase):
 def test_validator(self):
  t=(ROOT/'tools/docs/validate_v0310_summary.py').read_text(encoding='utf8');self.assertIn('Validation capture lock',t);self.assertIn('360/360',t)

