import unittest,yaml
from v039_support import ROOT
from v039_campaign import build_manifest
class TestSchedule(unittest.TestCase):
 def test_three_phases_and_14_episodes(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_9_training.yaml').read_text(encoding='utf8'));m=build_manifest(ROOT,c,c['runs'][0]);sc=[x for x in m['scenarios'] if not x['warmup']];self.assertEqual((len(sc),len({x['episode_id'] for x in sc})),(42,14));self.assertEqual({x['episode_phase'] for x in sc},{'phase_1','phase_2','phase_3'})
