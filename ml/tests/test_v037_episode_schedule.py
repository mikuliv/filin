import unittest,yaml
from v037_support import ROOT
from v037_campaign import build_manifest
class TestEpisodeSchedule(unittest.TestCase):
 def test_manifest_has_warmup_then_pairs(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_7_training.yaml').read_text(encoding='utf8'));m=build_manifest(ROOT,c,c['runs'][0]);self.assertEqual(len(m['scenarios']),34);self.assertTrue(all(x['warmup'] for x in m['scenarios'][:6]));self.assertEqual(len({x['episode_id'] for x in m['scenarios'][6:]}),14)
