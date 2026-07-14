import unittest
from v038_support import ROOT
from v038_campaign import build_manifest,load
class TestWarmupIsolation(unittest.TestCase):
 def test_six_unlabelled_warmups(self):
  c=load(ROOT/'lab/campaigns/v0_3_8_training.yaml');rows=build_manifest(ROOT,c,c['runs'][0])['scenarios'];warm=[x for x in rows if x['warmup']];self.assertEqual(len(warm),6);self.assertTrue(all(x['episode_id'] is None for x in warm))
