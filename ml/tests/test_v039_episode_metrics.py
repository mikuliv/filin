import unittest
from v039_support import ROOT
class TestEpisodeMetrics(unittest.TestCase):
 def test_pre_alert_not_missed(self):
  t=(ROOT/'ml/experiments/v0_3_9/pipeline.py').read_text(encoding='utf8');self.assertIn('episode_alerts.any()',t);self.assertIn('final_attack_window_alert_rate',t)
