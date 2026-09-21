import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from v037_support import ROOT
from data_access_guard import DataAccessError, DataAccessGuard


DATASETS = ROOT / "lab/output/datasets"


class TestDataAccessGuard(unittest.TestCase):
    def setUp(self):
        DATASETS.mkdir(parents=True, exist_ok=True)
        self.guard = DataAccessGuard(ROOT, ROOT / "ml/experiments/v0_3_7/data_access_policy.yaml")

    def test_v036_and_validation_before_freeze_are_blocked(self):
        with self.assertRaises(DataAccessError):
            self.guard.open_dataset(ROOT / "ml/experiments/v0_3_6/holdout_lock_manifest.yaml")
        with tempfile.TemporaryDirectory(dir=DATASETS) as directory:
            path = Path(directory) / "windows_network_sensor_v0_4_run_v037_validation_test.csv"
            path.write_text("x\n1\n", encoding="utf-8")
            with self.assertRaises(DataAccessError):
                self.guard.open_dataset(path, validation=True)

    def test_copy_with_known_v036_hash_is_blocked(self):
        with tempfile.TemporaryDirectory(dir=DATASETS) as directory:
            path = Path(directory) / "windows_network_sensor_v0_4_run_v037_train_copy.csv"
            path.write_text("copy", encoding="utf-8")
            digest = Mock()
            digest.hexdigest.return_value = self.guard.policy["forbidden_source_sha256"][0]
            with patch("data_access_guard.hashlib.sha256", return_value=digest):
                with self.assertRaises(DataAccessError):
                    self.guard.open_dataset(path)
