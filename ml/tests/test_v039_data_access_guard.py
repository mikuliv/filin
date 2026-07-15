import tempfile,unittest
from pathlib import Path
from v039_support import ROOT
from data_access_guard import DataAccessError,DataAccessGuard
class TestGuard(unittest.TestCase):
 def test_old_paths_blocked(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_9/data_access_policy.yaml')
  for version in ('v0_3_6','v0_3_7','v0_3_8'):
   self.assertRaises((DataAccessError,FileNotFoundError),g.open_dataset,ROOT/f'ml/reports/{version}/closed_set_metrics.json',purpose='training_rows')
 def test_forbidden_copy_hash_is_blocked(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_9/data_access_policy.yaml')
  # Digest rejection happens after canonical path resolution and before allowlist.
  g.forbidden_hashes.add('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
  with tempfile.TemporaryDirectory(dir=ROOT/'lab/output/datasets') as d:
   p=Path(d)/'windows_network_sensor_v0_4_run_v039_train_copy.csv';p.write_bytes(b'')
   self.assertRaises(DataAccessError,g.open_dataset,p,purpose='training_rows')
 def test_validation_before_freeze_blocked(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_9/data_access_policy.yaml');p=ROOT/'lab/output/datasets/windows_network_sensor_v0_4_run_v039_validation_missing.csv';self.assertRaises((DataAccessError,FileNotFoundError),g.open_dataset,p,purpose='validation_rows')
 def test_prediction_once(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_9/data_access_policy.yaml');g.claim_prediction(Path('missing'));self.assertRaises(DataAccessError,g.claim_prediction,Path('missing'))
