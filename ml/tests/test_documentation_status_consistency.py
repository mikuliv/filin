from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
