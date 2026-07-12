from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ml'/'training'))
from v034_data_access import assert_allowed_campaign,assert_allowed_dataset,load_policy
class DataPolicyTests(unittest.TestCase):
 def setUp(self): self.policy=load_policy(ROOT/'ml'/'experiments'/'v0_3_4'/'data_access_policy.yaml')
 def test_v033_is_blocked(self):
  with self.assertRaises(ValueError): assert_allowed_dataset(Path('lab/output/datasets/windows_network_sensor_v0_3_run_v033_mixed_001.csv'),self.policy)
 def test_only_declared_campaigns_allowed(self):
  assert_allowed_campaign('filin-v0.3.4-training','training',self.policy)
  with self.assertRaises(ValueError): assert_allowed_campaign('filin-v0.3.3-environment','training',self.policy)
