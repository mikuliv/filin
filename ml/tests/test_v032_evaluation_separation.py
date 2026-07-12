from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class V032EvaluationSeparationTests(unittest.TestCase):
    def test_external_evaluation_has_no_fit(self) -> None:
        text = (ROOT / "ml" / "experiments" / "v0_3_2" / "run_robustness_evaluation.py").read_text(encoding="utf-8")
        self.assertNotIn(".fit(", text)

    def test_reconstruction_is_separate_entry_point(self) -> None:
        text = (ROOT / "ml" / "experiments" / "v0_3_2" / "reconstruct_v031_baseline.py").read_text(encoding="utf-8")
        self.assertIn(".fit(", text)
        self.assertIn("run_v030_zeek_train_", text)
