import unittest,numpy as np
from ml.experiments.v0_3_10.pipeline import closed_set_metrics,CLASSES
class TestMetrics(unittest.TestCase):
 def test_perfect(self):
  y=np.array(CLASSES);p=np.eye(len(CLASSES));self.assertEqual(closed_set_metrics(y,p)['macro_f1'],1)
