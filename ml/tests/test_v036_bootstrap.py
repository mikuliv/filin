import unittest,pandas as pd
from v036_evaluation import _bootstrap
class BootstrapTests(unittest.TestCase):
 def test_cluster_sampling(self):
  rows=[]
  for run in ('a','b'):
   for label in ('benign','port_scan','auth_failures','web_probe','low_rate_dos','beacon_simulation'):rows.append({'run_id':run,'label':label,'prediction':label,'hard_negative':False})
  result=_bootstrap(pd.DataFrame(rows),10);self.assertEqual(result['sampling_unit'],'run_id');self.assertEqual(result['iterations'],10)
