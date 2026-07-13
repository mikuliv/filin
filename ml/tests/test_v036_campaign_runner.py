import argparse,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'lab/docker/services/traffic-client'))
sys.path.insert(0,str(ROOT/'lab/tools'))
from client import SCENARIOS,send_marker
from unittest.mock import Mock,patch
from scenario_executor import execute_scenario
class CampaignRunnerTests(unittest.TestCase):
 def test_all_holdout_workflows_registered(self):
  import yaml
  c=yaml.safe_load((ROOT/'lab/campaigns/v0_3_6_blind_holdout.yaml').read_text())
  self.assertTrue(set(c['execution_catalog']['benign']).issubset(SCENARIOS))

 def test_holdout_uses_observable_capture_window(self):
  observed={}
  def fake_run(*args):
   observed['duration']=args[4];observed['max_events']=args[5]
   return [],'',0
  manifest={'campaign_id':'filin-v0.3.6-blind-holdout','run_id':'run-test'}
  scenario={'scenario_id':'benign_ci_cd_agent','run_sequence':1,'label':'benign','duration_seconds':5}
  with tempfile.TemporaryDirectory() as directory, patch('scenario_executor.run_docker_scenario',side_effect=fake_run), patch('scenario_executor.time.sleep'):
   root=Path(directory)
   result=execute_scenario(manifest,scenario,root/'events.jsonl',root/'traffic.jsonl',False,ROOT/'lab/docker/docker-compose.lab.yml',ROOT/'lab/docker',.2,11601)
  self.assertEqual(result['status'],'completed')
  self.assertGreaterEqual(observed['duration'],4)
  self.assertEqual(observed['max_events'],8)

 def test_sensor_markers_are_redundant(self):
  response=Mock();response.raise_for_status.return_value=None
  args=argparse.Namespace(execution_id='run-test:1:test',marker_nonce='abc123')
  with patch('client.requests.post',return_value=response) as post,patch('client.time.sleep'):
   send_marker('end',args,{})
  self.assertEqual(post.call_count,5)
