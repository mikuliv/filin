import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'lab/campaigns'))
from v034_campaign import build_manifest,load_campaign
class BenignScenariosTests(unittest.TestCase):
 def test_sixteen_novel_benign(self):
  c=load_campaign(ROOT/'lab/campaigns/v0_3_6_blind_holdout.yaml');m=build_manifest(c,c['runs'][0],ROOT/'lab/scenarios');ids={x['scenario_id'] for x in m['scenarios'] if x['label']=='benign'};self.assertEqual(len(ids),16);self.assertTrue(all(x.startswith('benign_') for x in ids))
