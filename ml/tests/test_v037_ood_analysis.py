import unittest
from v037_support import *
from v037_ood_analysis import analyze
class TestOODAnalysis(unittest.TestCase):
 def test_ood_never_implies_attack(self):
  r=metric_rows();p=perfect_predictions(r);p['is_ood']=False;value=analyze(r,p,1.0);self.assertFalse(value['ood_automatically_mapped_to_attack']);self.assertFalse(value['threshold_changed_on_validation'])
