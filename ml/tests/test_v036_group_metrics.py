import unittest,pandas as pd
from v036_evaluation import metrics
class GroupMetricTests(unittest.TestCase):
 def test_error_is_visible(self):
  f=pd.DataFrame([{'label':'benign','prediction':'low_rate_dos','hard_negative':True},{'label':'port_scan','prediction':'port_scan','hard_negative':False}]);self.assertEqual(metrics(f)['false_positive_count'],1)
