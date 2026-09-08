from pathlib import Path
import unittest

from tools.docs.documentation_v2 import phase1_facts
from tools.docs.validate_documentation_freshness import stale_findings


ROOT = Path(__file__).resolve().parents[2]


class DocumentationStatusConsistencyTests(unittest.TestCase):
    def test_roadmap_preserves_both_track_boundaries(self):
        roadmap = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
        for marker in ("v0.3.18", "v0.3.19", "v0.4.4", "v0.4.5"):
            self.assertIn(marker, roadmap)
        self.assertIn("не реализован", roadmap)
        self.assertNotIn("sensor_ready_for_backend_integration=true", roadmap)

    def test_historical_prototypes_are_not_planned_current_capabilities(self):
        boundary = (ROOT / "docs/architecture/current-vs-historical.md").read_text(encoding="utf-8")
        self.assertIn("статический MITRE prototype", boundary)
        self.assertIn("backend/", boundary)
        self.assertIn("Исторические или демонстрационные", boundary)

    def test_stale_phase1_count_is_rejected(self):
        findings = stale_findings("Текущий план содержит 72 шаблона.", phase1_facts(ROOT))
        self.assertIn("stale_phase1_scenario_count", findings)
        self.assertIn("stale_phase1_scenario_count", stale_findings("Current Phase 1: 72 templates", phase1_facts(ROOT)))
        self.assertEqual(stale_findings("Режимы распределены по 72 шаблона.", phase1_facts(ROOT)), [])


if __name__ == "__main__":
    unittest.main()
