from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.docs.documentation_v2 import document_metadata, phase1_facts  # noqa: E402
from tools.docs.validate_documentation_maintenance import slug, validate  # noqa: E402


class DocumentationMaintenanceTests(unittest.TestCase):
    def test_status_metadata_and_machine_status_are_readable(self) -> None:
        metadata = document_metadata(ROOT / "docs/status/current-status.md", ROOT)
        status = yaml.safe_load((ROOT / "docs/status/project-status.yaml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["lifecycle"], "current")
        self.assertEqual(status["current_completed_stage"], status["mainline"]["latest_completed_stage"])
        self.assertEqual(status["next_allowed_stage"], status["mainline"]["next_allowed_stage"])
        self.assertFalse(status["external_validation_completed"])
        facts = phase1_facts(ROOT)
        self.assertEqual(status["independent_network_validation"]["latest_official_package_id"], facts["package_id"])
        self.assertEqual(status["independent_network_validation"]["execution_unit_count"], facts["execution_unit_count"])

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
