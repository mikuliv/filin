import unittest
from pathlib import Path

import yaml

from tools.docs.validate_documentation import validate

ROOT = Path(__file__).resolve().parents[2]


class TestResearchState(unittest.TestCase):
    def test_authoritative_state_is_safe_and_current(self):
        state = yaml.safe_load((ROOT / "docs/status/project-status.yaml").read_text(encoding="utf-8"))
        legacy = yaml.safe_load((ROOT / "docs/research-state.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["current_completed_stage"], "v0.3.15.5.1")
        self.assertEqual(state["latest_runtime_trial"], "v0.3.15.5.1")
        self.assertEqual(state["latest_corrective_audit"], "v0.3.15.1")
        self.assertEqual(state["latest_regression_analysis"], "v0.3.15.3")
        self.assertEqual(state["next_allowed_stage"], "v0.3.16")
        self.assertEqual(state["current_candidate"], "v03154:65a3dd912d845bc1")
        self.assertIsNone(state["blocked_stage"])
        self.assertFalse(state["backend_integration_ready"]); self.assertFalse(state["shadow_mode_ready"]); self.assertFalse(state["production_ready"])
        self.assertTrue(legacy["deprecated"]); self.assertEqual(legacy["authoritative_source"], "status/project-status.yaml")

    def test_documentation_validator_passes(self):
        self.assertEqual(validate(ROOT), [])


if __name__ == "__main__": unittest.main()
