import unittest
from unittest.mock import Mock,patch
from pathlib import Path
from v037_support import ROOT
from data_access_guard import DataAccessError,DataAccessGuard
class TestDataAccessGuard(unittest.TestCase):
 def test_v036_and_validation_before_freeze_are_blocked(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_7/data_access_policy.yaml')
  with self.assertRaises(DataAccessError):g.open_dataset(ROOT/'ml/experiments/v0_3_6/holdout_lock_manifest.yaml')
  path=ROOT/'lab/output/datasets/windows_network_sensor_v0_4_run_v037_validation_test.csv';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('x\n1\n')
  try:
   with self.assertRaises(DataAccessError):g.open_dataset(path,validation=True)
  finally:path.unlink(missing_ok=True)
 def test_copy_with_known_v036_hash_is_blocked(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_7/data_access_policy.yaml');path=ROOT/'lab/output/datasets/windows_network_sensor_v0_4_run_v037_train_copy.csv';path.write_text('copy')
  digest=Mock();digest.hexdigest.return_value=g.policy['forbidden_source_sha256'][0]
  try:
   with patch('data_access_guard.hashlib.sha256',return_value=digest):
    with self.assertRaises(DataAccessError):g.open_dataset(path)
  finally:path.unlink(missing_ok=True)
