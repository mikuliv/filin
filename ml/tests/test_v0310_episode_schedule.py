import unittest,yaml
from v0310_support import ROOT
from v0310_campaign import load,build_manifest
class TestSchedule(unittest.TestCase):
 def test_60_windows(self):
  c=load(ROOT/'lab/campaigns/v0_3_10_training.yaml');m=build_manifest(ROOT,c,c['runs'][0]);s=[x for x in m['scenarios'] if not x['warmup']];self.assertEqual((len(m['scenarios']),len(s),len({x['episode_id'] for x in s})),(60,54,18))

