import unittest
from v037_support import *
from pipeline import candidate_passes,window_metrics,episode_metrics
class TestModelSelection(unittest.TestCase):
 def test_perfect_candidate_passes(self):
  r=metric_rows();d=perfect_predictions(r);passed,_=candidate_passes(window_metrics(r,d),episode_metrics(r,d));self.assertTrue(passed)
