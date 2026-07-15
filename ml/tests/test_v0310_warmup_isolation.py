import unittest
from v0310_support import ROOT
from v0310_campaign import load,build_manifest
class TestWarmup(unittest.TestCase):
 def test_six_unlabelled_warmups(self):
  c=load(ROOT/'lab/campaigns/v0_3_10_training.yaml');m=build_manifest(ROOT,c,c['runs'][0]);w=[x for x in m['scenarios'] if x['warmup']];self.assertEqual(len(w),6);self.assertTrue(all(x['episode_id'] is None for x in w))

