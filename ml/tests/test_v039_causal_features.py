import unittest
import pandas as pd
from v039_support import ROOT
from network_sensor_v0_6 import CONTROL_PROFILE,build_causal_frame
class TestCausalFeatures(unittest.TestCase):
 def test_history_and_order(self):
  t=(ROOT/'ml/experiments/v0_3_9/pipeline.py').read_text(encoding='utf8');self.assertIn('history_depth=6',t);self.assertNotIn('sort_values(["run_id", "run_sequence"]',t)
 def test_future_mutation_does_not_change_current_vector(self):
  base={'run_id':'r','window_duration_seconds':20,'flow_count':1,'event_count':1,'episode_id':'e','label':'benign'}
  future={**base,'flow_count':2,'episode_id':'future','label':'port_scan'}
  changed={**future,'flow_count':999999,'label':'benign'}
  first=build_causal_frame(pd.DataFrame([base,future]).to_dict('records'),CONTROL_PROFILE,6).iloc[0]
  mutated=build_causal_frame(pd.DataFrame([base,changed]).to_dict('records'),CONTROL_PROFILE,6).iloc[0]
  pd.testing.assert_series_equal(first,mutated)
 def test_label_and_episode_id_are_not_features(self):
  self.assertNotIn('label',build_causal_frame([{'run_id':'r','label':'attack','episode_id':'secret'}],CONTROL_PROFILE,6).columns)
  self.assertNotIn('episode_id',build_causal_frame([{'run_id':'r','label':'attack','episode_id':'secret'}],CONTROL_PROFILE,6).columns)
