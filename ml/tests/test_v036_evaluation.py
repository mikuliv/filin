import unittest,pandas as pd
from ml.tests.v036_test_utils import ROOT
from v036_evaluation import metrics
class EvaluationTests(unittest.TestCase):
 def test_perfect_metrics(self):
  rows=[]
  for label in ('benign','port_scan','auth_failures','web_probe','low_rate_dos','beacon_simulation'):rows.append({'label':label,'prediction':label,'hard_negative':False})
  m=metrics(pd.DataFrame(rows));self.assertEqual(m['macro_f1'],1);self.assertEqual(m['false_positive_rate'],0)
