import unittest,pandas as pd
from v036_evaluation import _variant_metrics
class VariantMetricTests(unittest.TestCase):
 def test_variant_recall(self):
  f=pd.DataFrame([{'label':'benign','scenario_id':'a','prediction':'benign','confidence':.8,'benign_margin':.5},{'label':'benign','scenario_id':'a','prediction':'web_probe','confidence':.7,'benign_margin':-.2}]);self.assertEqual(_variant_metrics(f)['a']['benign_recall'],.5)
