from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd
from sklearn.dummy import DummyClassifier


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "experiments" / "v0_3_3"))

from environment_evaluation import evaluate_frozen, evaluate_policy, validate_feature_frame  # noqa: E402


class FrozenEnvironmentEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.features = ["flow_count", "total_bytes"]
        self.frame = pd.DataFrame({"flow_count": [1.0, 2.0], "total_bytes": [10.0, 20.0], "label": ["benign", "port_scan"]})
        self.model = DummyClassifier(strategy="most_frequent").fit(self.frame[self.features], self.frame["label"])

    def test_evaluation_predicts_without_a_fit_operation(self) -> None:
        result = evaluate_frozen(self.model, self.frame, self.features)
        self.assertEqual(result["rows"], 2)
        self.assertIn("macro_f1", result)

    def test_metadata_leakage_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "leakage"):
            validate_feature_frame(pd.DataFrame({"flow_count": [1], "run_id": ["run"]}), ["flow_count", "run_id"])

    def test_policy_can_report_a_negative_result_without_raising(self) -> None:
        metric = {"macro_f1": 0.1, "attack_macro_recall": 0.0, "collapsed_attack_precision": 0.0, "collapsed_attack_recall": 0.0, "per_class": {"benign": {"recall": 0.0}}}
        policy = {"minimum_group_macro_f1": 0.6, "minimum_group_benign_recall": 0.7, "minimum_group_attack_macro_recall": 0.6, "minimum_overall_macro_f1": 0.7, "minimum_overall_benign_recall": 0.85, "minimum_overall_attack_macro_recall": 0.8, "minimum_collapsed_attack_precision": 0.8, "minimum_collapsed_attack_recall": 0.8}
        result = evaluate_policy({"mixed": metric}, metric, policy)
        self.assertFalse(result["environment_robustness_passed"])

