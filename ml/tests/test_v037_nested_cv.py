import unittest,yaml
from v037_support import ROOT
class TestNestedCV(unittest.TestCase):
 def test_grouped_splits_frozen(self):
  p=yaml.safe_load((ROOT/'ml/experiments/v0_3_7/model_selection_policy.yaml').read_text(encoding='utf8'));self.assertEqual(p['outer_cv']['n_splits'],6);self.assertEqual(p['inner_cv']['n_splits'],4);self.assertEqual(p['outer_cv']['group'],'run_id')
