import unittest,pandas as pd
from ml.tests.v036_test_utils import ROOT
from v036_evaluation import metrics
class EvaluationTests(unittest.TestCase):
 def test_perfect_metrics(self):
  rows=[]
  for label in ('benign','port_scan','auth_failures','web_probe','low_rate_dos','beacon_simulation'):rows.append({'label':label,'prediction':label,'hard_negative':False})
  m=metrics(pd.DataFrame(rows));self.assertEqual(m['macro_f1'],1);self.assertEqual(m['false_positive_rate'],0)
 def test_global_class_precision_counts_false_positives(self):
  f=pd.DataFrame([{'label':'benign','prediction':'low_rate_dos','hard_negative':False},{'label':'low_rate_dos','prediction':'low_rate_dos','hard_negative':False}])
  self.assertEqual(metrics(f)['per_class']['low_rate_dos']['precision'],.5)
