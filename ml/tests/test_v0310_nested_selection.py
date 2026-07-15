import unittest,yaml
from v0310_support import ROOT
class TestNested(unittest.TestCase):
 def test_limits(self):
  g=yaml.safe_load((ROOT/'ml/experiments/v0_3_10/decision_grid.yaml').read_text(encoding='utf8'));self.assertEqual(g['limits']['total_combinations'],101);self.assertIn('StratifiedGroupKFold',(ROOT/'ml/experiments/v0_3_10/pipeline.py').read_text(encoding='utf8'))

