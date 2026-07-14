import unittest
import pandas as pd
from v038_support import raw_row
from network_sensor_v0_6 import EVIDENCE_PROFILE,build_causal_frame
from v038_support import load_v038
class TestCausalFeatures(unittest.TestCase):
 def test_future_changes_do_not_change_past(self):
  rows=[raw_row(flow=x) for x in (1,2,3)];base=build_causal_frame(rows,EVIDENCE_PROFILE);rows[-1]['flow_count']=999;changed=build_causal_frame(rows,EVIDENCE_PROFILE);self.assertTrue(base.iloc[:-1].equals(changed.iloc[:-1]))
 def test_state_resets_between_runs(self):
  mixed=build_causal_frame([raw_row('a',flow=10),raw_row('b',flow=1)],EVIDENCE_PROFILE);fresh=build_causal_frame([raw_row('b',flow=1)],EVIDENCE_PROFILE);self.assertTrue(mixed.iloc[1].equals(fresh.iloc[0]))
 def test_dataset_order_does_not_require_leaky_run_sequence(self):
  pipeline=load_v038('v038_pipeline_order_test','ml/experiments/v0_3_8/pipeline.py');rows=[]
  for index in range(3):
   row=raw_row(flow=index+1);row.update({'warmup':index==0,'execution_id':f'e{index}','episode_class':'benign'});rows.append(row)
  metadata,features=pipeline.build_feature_frame(pd.DataFrame(rows),EVIDENCE_PROFILE);self.assertEqual(len(metadata),2);self.assertEqual(len(features),2)
