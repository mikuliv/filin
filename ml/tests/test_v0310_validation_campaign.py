import unittest,yaml
from v0310_support import ROOT
class TestCampaign(unittest.TestCase):
 def test_counts(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_10_internal_validation.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),6);self.assertEqual(sum(1 for x in c['runs'] if 'validation' in x['run_id']),6)

