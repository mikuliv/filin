from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lab'/'campaigns'))
from v034_campaign import build_manifest,load_campaign
class CampaignTests(unittest.TestCase):
 def test_training_and_validation_counts(self):
  train=load_campaign(ROOT/'lab'/'campaigns'/'v0_3_4_training.yaml'); valid=load_campaign(ROOT/'lab'/'campaigns'/'v0_3_4_internal_validation.yaml')
  self.assertEqual(len(train['runs']),12);self.assertEqual(len(valid['runs']),6)
  manifest=build_manifest(train,train['runs'][0],ROOT/'lab'/'scenarios')
  self.assertEqual(manifest['scenario_count'],21);self.assertEqual(sum(x['label']=='benign' for x in manifest['scenarios']),16)
