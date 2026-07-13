import unittest,yaml
from v037_support import ROOT
class TestValidationCampaign(unittest.TestCase):
 def test_six_validation_only_runs(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_7_internal_validation.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),6);self.assertTrue(all('validation' in x['run_id'] for x in c['runs']))
