from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab/background"))
from background_safety import validate_background_config  # noqa: E402


class V033BackgroundSafetyTests(unittest.TestCase):
    def test_rejects_excessive_rate(self):
        with self.assertRaises(ValueError):
            validate_background_config({"target": "target-web", "clients": 1, "actions_per_second": 3.1, "actions_per_interval": 1})

    def test_rejects_external_target(self):
        with self.assertRaises(ValueError):
            validate_background_config({"target": "external", "clients": 1, "actions_per_second": 1, "actions_per_interval": 1})
