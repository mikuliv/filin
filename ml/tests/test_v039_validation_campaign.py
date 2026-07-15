import unittest,yaml
from v039_support import ROOT
class TestValidation(unittest.TestCase):
 def test_totals_and_new_seeds(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_9_internal_validation.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),6);self.assertEqual(c['scored_windows'],42);self.assertTrue(all(r['random_seed']>=15101 for r in c['runs']))
