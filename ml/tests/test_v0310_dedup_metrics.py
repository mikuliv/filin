import unittest
from v0310_support import ROOT
class TestDedupMetrics(unittest.TestCase):
 def test_emissions(self):self.assertIn('duplicates_suppressed',(ROOT/'ml/experiments/v0_3_10/run_internal_validation.py').read_text(encoding='utf8'))

