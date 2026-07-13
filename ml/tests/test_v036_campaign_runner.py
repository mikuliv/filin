import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'lab/docker/services/traffic-client'))
from client import SCENARIOS
class CampaignRunnerTests(unittest.TestCase):
 def test_all_holdout_workflows_registered(self):
  import yaml
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_6_blind_holdout.yaml').read_text())
  self.assertTrue(set(c['execution_catalog']['benign']).issubset(SCENARIOS))
