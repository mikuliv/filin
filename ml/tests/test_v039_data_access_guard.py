import tempfile,unittest
from pathlib import Path
from v039_support import ROOT
from data_access_guard import DataAccessError,DataAccessGuard
class TestGuard(unittest.TestCase):
 def test_old_paths_blocked(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_9/data_access_policy.yaml');self.assertRaises((DataAccessError,FileNotFoundError),g.open_dataset,ROOT/'ml/reports/v0_3_8/closed_set_metrics.json',purpose='training_rows')
 def test_validation_before_freeze_blocked(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_9/data_access_policy.yaml');p=ROOT/'lab/output/datasets/windows_network_sensor_v0_4_run_v039_validation_missing.csv';self.assertRaises((DataAccessError,FileNotFoundError),g.open_dataset,p,purpose='validation_rows')
 def test_prediction_once(self):
  g=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_9/data_access_policy.yaml');g.claim_prediction(Path('missing'));self.assertRaises(DataAccessError,g.claim_prediction,Path('missing'))
