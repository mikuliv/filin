from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class DocumentationMetricsConsistencyTests(unittest.TestCase):
    def test_evergreen_experiment_index_does_not_copy_historical_metrics(self):
        text = (ROOT / "docs/experiments.md").read_text(encoding="utf-8")
        for historical_value in ("0.918", "0.933", "0.972", "0.979", "12 robustness-runs", "156 windows"):
            self.assertNotIn(historical_value, text)
        self.assertIn("stage-specific frozen reports", text)

    def test_evergreen_testing_guide_has_no_stale_passed_counter(self):
        text = (ROOT / "docs/getting-started/testing.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b\d{3,5}\s+passed\b", text))
        self.assertIn("0 failed", text)


if __name__ == "__main__":
    unittest.main()
