import unittest
from v039_support import ROOT,record
from pipeline import attach_manifest_timestamps
class TestCausalDecision(unittest.TestCase):
 def test_episode_id_rejected(self):
  from v039_alert_lifecycle import AlertLifecycle
  life=AlertLifecycle();self.assertRaises(ValueError,life.update,{'episode_id':'x'})
 def test_future_record_mutations_do_not_change_past_decision(self):
  from v039_alert_lifecycle import AlertLifecycle
  first_a=AlertLifecycle().update(record());first_b=AlertLifecycle().update(record())
  future=record('web_probe');future['joint_probabilities']['web_probe']=.999;future['conformal_set']=[];future['support_margins']['web_probe']=-999
  self.assertEqual(first_a,first_b)
 def test_lifecycle_timestamp_is_mapped_without_episode_metadata(self):
  import pandas as pd,yaml
  manifest=ROOT/'lab/output/runs/run_v039_train_early_001/scenario_manifest.yaml'
  if not manifest.exists():self.skipTest('runtime manifest отсутствует')
  item=yaml.safe_load(manifest.read_text(encoding='utf8'))['scenarios'][0]
  mapped=attach_manifest_timestamps(pd.DataFrame([{'run_id':'run_v039_train_early_001','execution_id':item['execution_id']}]),ROOT/'lab/output')
  self.assertEqual(mapped.loc[0,'planned_started_at'],item['planned_started_at']);self.assertNotIn('episode_id',mapped.columns)
