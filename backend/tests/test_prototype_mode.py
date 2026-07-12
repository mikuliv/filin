from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import capabilities, health  # noqa: E402


class PrototypeModeTests(unittest.TestCase):
    def test_health_and_capabilities_expose_prototype_status(self) -> None:
        self.assertTrue(health()["prototype_mode"])
        self.assertTrue(capabilities()["prototype_mode"])
        self.assertFalse(capabilities()["network_sensor_model_integrated"])
