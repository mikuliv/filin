import unittest
from pathlib import Path

import yaml

from tools.docs.validate_documentation import validate

ROOT = Path(__file__).resolve().parents[2]


class TestResearchState(unittest.TestCase):
    def test_authoritative_state_is_safe_and_current(self):
        state = yaml.safe_load((ROOT / "docs/research-state.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["latest_completed_stage"], "v0.3.11")
        self.assertEqual(state["latest_completed_result"], "internal_validation_policy_passed")
        self.assertEqual(state["next_allowed_stage"]["kind"], "frozen_multi_benchmark_regression")
        self.assertFalse(state["backend_integration_allowed"]); self.assertFalse(state["shadow_mode_allowed"]); self.assertFalse(state["production_ready"])

    def test_documentation_validator_passes(self):
        self.assertEqual(validate(ROOT), [])


if __name__ == "__main__": unittest.main()
