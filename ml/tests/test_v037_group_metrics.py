import unittest
from v037_support import *
from run_internal_validation import subset_reports
class TestGroupMetrics(unittest.TestCase):
 def test_support_is_partitioned(self):
  r=metric_rows();r.loc[0,'environment_group']='h';out=subset_reports(r,perfect_predictions(r),'environment_group');self.assertEqual(sum(x['window_metrics']['support'] for x in out.values()),len(r))
