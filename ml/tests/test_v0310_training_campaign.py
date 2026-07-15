import unittest,yaml
from v0310_support import ROOT
class TestCampaign(unittest.TestCase):
 def test_counts(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_10_training.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),12);self.assertEqual(c['scored_windows'],54);self.assertEqual(len({x['random_seed'] for x in c['runs']}),12)

