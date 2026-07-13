import unittest
from v037_support import *
from network_sensor_v0_5 import AssetState
class TestAssetState(unittest.TestCase):
 def test_state_resets_between_runs(self):
  s=AssetState(4);s.vector(raw_feature_row('a',10),'network_sensor_v0_5_temporal');v=s.vector(raw_feature_row('b',2),'network_sensor_v0_5_temporal');self.assertEqual(v['delta_flows_per_second'],0)
