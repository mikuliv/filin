import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from v038_support import ROOT, load_v038


guard_module = load_v038("v038_data_access_guard_unique", "ml/experiments/v0_3_8/data_access_guard.py")
DataAccessError = guard_module.DataAccessError
DataAccessGuard = guard_module.DataAccessGuard
DATASETS = ROOT / "lab/output/datasets"


class TestDataAccessGuard(unittest.TestCase):
    def setUp(self):
        DATASETS.mkdir(parents=True, exist_ok=True)
        self.guard = DataAccessGuard(ROOT, ROOT / "ml/experiments/v0_3_8/data_access_policy.yaml")

    def test_old_paths_blocked(self):
        with tempfile.TemporaryDirectory(dir=DATASETS) as directory:
            path = Path(directory) / "windows_network_sensor_v0_4_run_v037_train_fixture.csv"
            path.write_text("x\n1\n", encoding="utf-8")
            with self.assertRaises(DataAccessError):
                self.guard.open_dataset(path, purpose="training_rows")

    def test_validation_before_freeze_blocked(self):
        with tempfile.TemporaryDirectory(dir=DATASETS) as directory:
            path = Path(directory) / "windows_network_sensor_v0_4_run_v038_validation_test.csv"
            path.write_text("x\n1\n", encoding="utf-8")
            with self.assertRaises(DataAccessError):
                self.guard.open_dataset(path, purpose="validation_rows")

    def test_old_hash_copy_blocked(self):
        with tempfile.TemporaryDirectory(dir=DATASETS) as directory:
            path = Path(directory) / "windows_network_sensor_v0_4_run_v038_train_hash_copy.csv"
            path.write_text("test fixture", encoding="utf-8")
            digest = Mock()
            digest.hexdigest.return_value = self.guard.policy["forbidden_source_sha256"][0]
            with patch.object(guard_module.hashlib, "sha256", return_value=digest):
                with self.assertRaises(DataAccessError):
                    self.guard.open_dataset(path, purpose="training_rows")
