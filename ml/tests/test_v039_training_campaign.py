import unittest,yaml
from v039_support import ROOT
class TestTraining(unittest.TestCase):
 def test_totals(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_9_training.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),12);self.assertEqual(sum(c[x] for x in ('warmup_windows','scored_windows')),48);self.assertEqual(len({r['random_seed'] for r in c['runs']}),12)
 def test_dns_capture_role_is_explicitly_allowed(self):
  text=(ROOT/'lab/tools/scenario_executor.py').read_text(encoding='utf8');self.assertIn('episode_first_training',text);self.assertIn('episode_first_validation',text)
