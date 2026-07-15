import unittest
from v0310_support import ROOT
class TestMetrics(unittest.TestCase):
 def test_report_named(self):self.assertIn('strong_path_metrics',(ROOT/'ml/experiments/v0_3_10/run_internal_validation.py').read_text(encoding='utf8'))

