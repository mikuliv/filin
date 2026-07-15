import unittest,numpy as np
from v039_support import ROOT,CLASSES
from pipeline import closed_set_metrics
class TestClosed(unittest.TestCase):
 def test_perfect(self):
  y=np.array(CLASSES);m=closed_set_metrics(y,np.eye(6));self.assertEqual(m['macro_f1'],1);self.assertEqual(m['FPR'],0)
