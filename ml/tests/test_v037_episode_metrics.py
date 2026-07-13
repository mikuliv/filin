import unittest
from v037_support import *
from pipeline import episode_metrics
class TestEpisodeMetrics(unittest.TestCase):
 def test_episode_detection(self):
  rows=metric_rows();pred=perfect_predictions(rows);pred[['run_id','episode_id','label']]=rows[['run_id','episode_id','label']];m=episode_metrics(rows,pred);self.assertEqual(m['attack_episode_recall'],1);self.assertEqual(m['benign_episode_false_alert_rate'],0)
