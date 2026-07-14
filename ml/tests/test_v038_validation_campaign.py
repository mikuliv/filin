import unittest,yaml
from v038_support import ROOT
class TestValidationCampaign(unittest.TestCase):
 def test_totals_and_new_seeds(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_8_internal_validation.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),6);self.assertEqual(c['scored_windows']*6,216);self.assertEqual({x['random_seed'] for x in c['runs']},{14401,14402,14501,14502,14601,14602})
