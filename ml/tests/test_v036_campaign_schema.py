import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'lab/campaigns'))
from v034_campaign import load_campaign
class CampaignSchemaTests(unittest.TestCase):
 def test_runs_groups_and_seeds(self):
  c=load_campaign(ROOT/'lab/campaigns/v0_3_6_blind_holdout.yaml');self.assertEqual(len(c['runs']),12);self.assertEqual(len({x['group'] for x in c['runs']}),4);self.assertEqual([x['random_seed'] for x in c['runs']],[11601,11602,11603,11701,11702,11703,11801,11802,11803,11901,11902,11903])
