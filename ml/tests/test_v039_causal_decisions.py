import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

from v039_support import record
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
  run_id = 'test_causal_timestamp_mapping'
  item = {
   'execution_id': f'{run_id}:1:fixture',
   'planned_started_at': '2026-01-01T00:00:00Z',
   'episode_id': 'metadata-must-not-leak',
  }
  with tempfile.TemporaryDirectory() as directory:
   output_root = Path(directory)
   manifest = output_root / 'runs' / run_id / 'scenario_manifest.yaml'
   manifest.parent.mkdir(parents=True)
   manifest.write_text(yaml.safe_dump({'scenarios': [item]}), encoding='utf-8')
   mapped = attach_manifest_timestamps(
    pd.DataFrame([{'run_id': run_id, 'execution_id': item['execution_id']}]),
    output_root,
   )
  self.assertEqual(mapped.loc[0, 'planned_started_at'], item['planned_started_at'])
  self.assertNotIn('episode_id', mapped.columns)
