import unittest,yaml
from collections import Counter
from v038_support import ROOT
from v038_campaign import build_manifest,load
class TestScenarioBalance(unittest.TestCase):
 def test_exact_support(self):
  for file,expected in [('v0_3_8_training.yaml',6),('v0_3_8_internal_validation.yaml',3)]:
   c=load(ROOT/'lab/campaigns'/file);counts=Counter()
   for run in c['runs']:
    for row in build_manifest(ROOT,c,run)['scenarios']:
     if not row['warmup'] and row['episode_class']=='benign':counts[row['scenario_id']]+=1
   self.assertTrue(all(value==expected*3 for value in counts.values()));self.assertEqual(len(counts),14)
