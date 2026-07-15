import unittest
from v039_support import ROOT
class TestGroupMetrics(unittest.TestCase):
 def test_three_groups(self):
  t=(ROOT/'lab/campaigns/v0_3_9_internal_validation.yaml').read_text(encoding='utf8');self.assertEqual(sum(x in t for x in ('unseen_early_signal_shift','cross_workflow_interference','conflict_and_recovery_shift')),3)
