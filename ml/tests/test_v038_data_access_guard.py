import shutil,tempfile,unittest
from pathlib import Path
from v038_support import ROOT,load_v038
guard_module=load_v038('v038_data_access_guard_unique','ml/experiments/v0_3_8/data_access_guard.py');DataAccessError=guard_module.DataAccessError;DataAccessGuard=guard_module.DataAccessGuard
class TestDataAccessGuard(unittest.TestCase):
 def setUp(self):self.guard=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_8/data_access_policy.yaml')
 def test_old_paths_blocked(self):
  path=next((ROOT/'lab/output/datasets').glob('*run_v037*csv'))
  with self.assertRaises(DataAccessError):self.guard.open_dataset(path,purpose='training_rows')
 def test_validation_before_freeze_blocked(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'lab/output/datasets') as d:
   path=Path(d)/'windows_network_sensor_v0_4_run_v038_validation_test.csv';path.write_text('x\n1\n')
   with self.assertRaises(DataAccessError):self.guard.open_dataset(path,purpose='validation_rows')
 def test_old_hash_copy_blocked(self):
  source=next((ROOT/'lab/output/datasets').glob('*run_v037*csv'))
  target=ROOT/'lab/output/datasets/windows_network_sensor_v0_4_run_v038_train_hash_copy.csv';shutil.copyfile(source,target)
  try:
   with self.assertRaises(DataAccessError):self.guard.open_dataset(target,purpose='training_rows')
  finally:target.unlink(missing_ok=True)
