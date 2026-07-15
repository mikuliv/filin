import unittest,yaml
from v039_support import ROOT
import sys
sys.path.insert(0,str(ROOT/'lab/docker/services/traffic-client'))
from future_workflows import WORKFLOW_PLANS
class TestTraining(unittest.TestCase):
 def test_totals(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_9_training.yaml').read_text(encoding='utf8'));self.assertEqual(len(c['runs']),12);self.assertEqual(sum(c[x] for x in ('warmup_windows','scored_windows')),48);self.assertEqual(len({r['random_seed'] for r in c['runs']}),12)
 def test_dns_capture_role_is_explicitly_allowed(self):
  text=(ROOT/'lab/tools/scenario_executor.py').read_text(encoding='utf8');self.assertIn('episode_first_training',text);self.assertIn('episode_first_validation',text)
 def test_all_new_benign_scenarios_have_executable_workflows(self):
  for name in ('v0_3_9_training_benign.yaml','v0_3_9_validation_benign.yaml'):
   catalog=yaml.safe_load((ROOT/'lab/scenarios'/name).read_text(encoding='utf8'))
   self.assertTrue(all(row['scenario_id'] in WORKFLOW_PLANS for row in catalog['scenarios']))
