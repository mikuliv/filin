from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.docs.validate_documentation_maintenance import (  # noqa: E402
    front_matter,
    slug,
    validate,
)


class DocumentationMaintenanceTests(unittest.TestCase):
    def test_status_front_matter_is_machine_readable(self) -> None:
        status = front_matter(ROOT / "docs/status/current-status.md")
        self.assertEqual(status["latest_completed_stage"], "v0.3.18")
        self.assertEqual(status["next_allowed_stage"], "v0.3.19")
        self.assertFalse(status["external_trial_execution_allowed"])

    def test_heading_slug_is_stable(self) -> None:
        self.assertEqual(slug("Текущий статус"), "текущий-статус")
        self.assertEqual(slug("README: до и после"), "readme-до-и-после")

    def test_readme_points_to_documentation_hub(self) -> None:
        self.assertIn("docs/index.md", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_documentation_gate_passes(self) -> None:
        result = validate(ROOT)
        self.assertTrue(result["valid"], "\n".join(result["errors"]))


if __name__ == "__main__":
    unittest.main()
