import unittest,yaml
from v037_support import ROOT
from v037_campaign import build_manifest
class TestCampaignIntegrity(unittest.TestCase):
 def test_each_run_has_exact_composition(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_7_training.yaml').read_text(encoding='utf8'))
  for run in c['runs']:
   m=build_manifest(ROOT,c,run);self.assertEqual(sum(not x['warmup'] for x in m['scenarios']),28);self.assertEqual(sum(x['label']=='benign' and not x['warmup'] for x in m['scenarios']),18)
 def test_validation_uses_execution_isolated_capture(self):
  runner=(ROOT/'lab/campaigns/v037_runner.py').read_text(encoding='utf-8')
  executor=(ROOT/'lab/tools/scenario_executor.py').read_text(encoding='utf-8')
  compose=(ROOT/'lab/docker/docker-compose.lab.yml').read_text(encoding='utf-8')
  self.assertIn("'FILIN_SCENARIO_CAPTURE_DIR'",runner)
  self.assertIn("len(captures)!=34",runner)
  self.assertIn('"--marker-log", "/capture/marker_control.jsonl"',executor)
  self.assertIn('"-B", "16384", "--immediate-mode"',compose)
  self.assertIn('"--marker-copies", "5"',executor)
