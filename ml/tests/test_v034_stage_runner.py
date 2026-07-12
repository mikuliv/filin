from __future__ import annotations
import subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class StageRunnerTests(unittest.TestCase):
 def test_preflight_does_not_execute_campaign(self):
  command=[sys.executable,str(ROOT/'lab'/'training'/'run_v0_3_4_stage.py'),'--training-campaign',str(ROOT/'lab'/'campaigns'/'v0_3_4_training.yaml'),'--validation-campaign',str(ROOT/'lab'/'campaigns'/'v0_3_4_internal_validation.yaml'),'--data-access-policy',str(ROOT/'ml'/'experiments'/'v0_3_4'/'data_access_policy.yaml'),'--strict']
  result=subprocess.run(command,capture_output=True,text=True,check=True)
  self.assertIn('preflight_only_no_campaign_execution',result.stdout)
