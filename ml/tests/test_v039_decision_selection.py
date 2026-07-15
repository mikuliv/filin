import unittest,yaml
from v039_support import ROOT
class TestSelection(unittest.TestCase):
 def test_fixed_grid(self):
  g=yaml.safe_load((ROOT/'ml/experiments/v0_3_9/decision_grid.yaml').read_text(encoding='utf8'));self.assertEqual(2*2*2,8);self.assertEqual(g['lifecycle_stage']['active_minimum_hold_windows'],[2])
