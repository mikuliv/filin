from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "analysis"))
from v033_forensic_audit import psi  # noqa: E402


class ForensicAuditTests(unittest.TestCase):
    def test_psi_accepts_boolean_sensor_feature(self) -> None:
        self.assertGreaterEqual(psi(pd.Series([True, False, True]), pd.Series([False, False, True])), 0.0)
