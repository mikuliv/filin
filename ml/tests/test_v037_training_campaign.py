import unittest,yaml
from collections import Counter
from v037_support import ROOT
class TestTrainingCampaign(unittest.TestCase):
 def test_twelve_unique_runs_and_seeds(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_7_training.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),12);self.assertEqual(len({x['random_seed'] for x in c['runs']}),12);self.assertEqual(c['scored_windows'],28)
