import unittest,yaml
from v039_support import ROOT
from v039_campaign import build_manifest
class TestWarmup(unittest.TestCase):
 def test_six_unlabelled_training_rows(self):
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_9_training.yaml').read_text(encoding='utf8'));m=build_manifest(ROOT,c,c['runs'][0]);self.assertEqual(sum(x['warmup'] for x in m['scenarios']),6)
