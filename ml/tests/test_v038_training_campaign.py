import unittest,yaml
from v038_support import ROOT
class TestTrainingCampaign(unittest.TestCase):
 def test_totals(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_8_training.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),12);self.assertEqual(c['scored_windows']*12,432);self.assertEqual(c['warmup_windows']*12,72)
