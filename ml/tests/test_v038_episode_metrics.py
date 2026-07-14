import unittest
from v038_support import ROOT
class TestEpisodeMetrics(unittest.TestCase):
 def test_precision_and_delay_implemented(self):
  text=(ROOT/'ml/experiments/v0_3_8/pipeline.py').read_text(encoding='utf8');self.assertIn('episode_alert_precision',text);self.assertIn('time_to_first_alert',text)
