import unittest
from v037_support import *
from run_internal_validation import benign_variant_reports
class TestVariantMetrics(unittest.TestCase):
 def test_benign_variant_recall(self):
  r=metric_rows();p=perfect_predictions(r);p[['run_id','label','variant_id']]=r[['run_id','label','variant_id']];value=benign_variant_reports(r,p);self.assertEqual(value['variants']['v']['benign_recall'],1)
