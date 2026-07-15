import unittest,yaml
from v039_support import ROOT
class TestTraining(unittest.TestCase):
 def test_totals(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_9_training.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),12);self.assertEqual(sum(c[x] for x in ('warmup_windows','scored_windows')),48);self.assertEqual(len({r['random_seed'] for r in c['runs']}),12)
