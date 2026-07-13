import unittest
from v037_support import *
from pipeline import window_metrics
class TestWindowMetrics(unittest.TestCase):
 def test_perfect_predictions(self):
  m=window_metrics(metric_rows(),perfect_predictions());self.assertEqual(m['benign_recall'],1);self.assertEqual(m['attack_alert_recall'],1);self.assertEqual(m['false_positive_rate'],0)
