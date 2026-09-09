from __future__ import annotations

import json
import sys
import tempfile
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

    def test_reviewed_language_metadata_is_propagated_only_for_listed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "docs/audit"
            audit.mkdir(parents=True)
            (root / "README.md").write_text("# Проект\n", encoding="utf-8")
            (root / "OTHER.md").write_text("# Другой документ\n", encoding="utf-8")
            (audit / "documentation_inventory_v2.json").write_text(json.dumps({
                "documents": [
                    {"path": "README.md", "lifecycle_status": "current"},
                    {"path": "OTHER.md", "lifecycle_status": "current"},
                ]
            }), encoding="utf-8")
            (audit / "documentation_metadata_overrides_v2.json").write_text(json.dumps({
                "reviewed_current_paths": ["README.md"]
            }), encoding="utf-8")

            reviewed = document_metadata(root / "README.md", root)
            not_reviewed = document_metadata(root / "OTHER.md", root)
            self.assertTrue(reviewed["reviewed_in_current_language_pass"])
            self.assertEqual(reviewed["last_reviewed_stage"], "v0.4.7.3")
            self.assertFalse(not_reviewed["reviewed_in_current_language_pass"])


if __name__ == "__main__":
    unittest.main()
