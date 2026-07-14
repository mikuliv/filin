import unittest
from v038_support import ROOT
from v038_campaign import build_manifest,load
class TestEpisodeSchedule(unittest.TestCase):
 def test_three_phases(self):
  c=load(ROOT/'lab/campaigns/v0_3_8_training.yaml');m=build_manifest(ROOT,c,c['runs'][0]);scored=[x for x in m['scenarios'] if not x['warmup']];self.assertEqual(len(scored),36);self.assertEqual({x['episode_phase'] for x in scored},{'phase_1','phase_2','phase_3'});self.assertEqual(len({x['episode_id'] for x in scored}),12)
