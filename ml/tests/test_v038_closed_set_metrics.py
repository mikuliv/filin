import importlib.util,unittest
import numpy as np
from v038_support import ROOT
spec=importlib.util.spec_from_file_location('v038_metrics_unique',ROOT/'ml/experiments/v0_3_8/pipeline.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class TestClosedMetrics(unittest.TestCase):
 def test_perfect(self):
  labels=mod.CLASSES;metrics=mod.closed_set_metrics(labels,np.eye(6));self.assertEqual(metrics['macro_f1'],1);self.assertEqual(metrics['FPR'],0)
