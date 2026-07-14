import unittest
from v038_support import ROOT
class TestSupportMetrics(unittest.TestCase):
 def test_required_metrics(self):self.assertIn('unsupported_attack_rate',(ROOT/'ml/experiments/v0_3_8/pipeline.py').read_text(encoding='utf8'))
