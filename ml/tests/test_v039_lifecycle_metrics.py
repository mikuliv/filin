import unittest
from v039_support import ROOT
class TestLifecycleMetrics(unittest.TestCase):
 def test_transitions_counted(self):
  t=(ROOT/'ml/experiments/v0_3_9/run_internal_validation.py').read_text(encoding='utf8');self.assertIn('pending_to_active_count',t);self.assertIn('alert_cancelled_by_one_benign_window_count',t)
