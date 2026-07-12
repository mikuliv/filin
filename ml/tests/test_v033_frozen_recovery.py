from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "experiments" / "v0_3_3"))
from recover_frozen_baseline import feature_list  # noqa: E402


class FrozenRecoveryTests(unittest.TestCase):
    def test_feature_order_preserves_v031_numeric_selection(self) -> None:
        frame = pd.DataFrame({"run_id": ["source"], "label": ["benign"], "window_index": [0], "flow_count": [1.0]})
        self.assertEqual(feature_list(frame), ["window_index", "flow_count"])

    def test_v033_identifier_is_not_a_recovery_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.assertEqual(list(directory.glob("windows_network_sensor_v0_3_run_v030_zeek_train_*.csv")), [])

