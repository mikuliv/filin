import unittest
from v037_support import *
from network_sensor_v0_5 import build_causal_frame
class TestCausalFeatures(unittest.TestCase):
 def test_future_mutation_does_not_change_past(self):
  rows=[raw_feature_row(flow=x) for x in (1,2,3)];a=build_causal_frame(rows,'network_sensor_v0_5_contextual');rows[-1]['flow_count']=999;b=build_causal_frame(rows,'network_sensor_v0_5_contextual');self.assertTrue(a.iloc[:-1].equals(b.iloc[:-1]))
