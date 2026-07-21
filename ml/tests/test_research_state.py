import unittest
from pathlib import Path

import yaml

from tools.docs.validate_documentation import validate

ROOT = Path(__file__).resolve().parents[2]


class TestResearchState(unittest.TestCase):
    def test_authoritative_state_is_safe_and_current(self):
        state = yaml.safe_load((ROOT / "docs/status/project-status.yaml").read_text(encoding="utf-8"))
        legacy = yaml.safe_load((ROOT / "docs/research-state.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["current_completed_stage"], "v0.3.15.1")
        self.assertEqual(state["latest_runtime_trial"], "v0.3.15")
        self.assertIsNone(state["next_allowed_stage"])
        self.assertEqual(state["blocked_stage"], "v0.3.16")
        self.assertFalse(state["backend_integration_ready"]); self.assertFalse(state["shadow_mode_ready"]); self.assertFalse(state["production_ready"])
        self.assertTrue(legacy["deprecated"]); self.assertEqual(legacy["authoritative_source"], "status/project-status.yaml")

    def test_documentation_validator_passes(self):
        self.assertEqual(validate(ROOT), [])


if __name__ == "__main__": unittest.main()
