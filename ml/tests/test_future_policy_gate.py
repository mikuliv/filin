import unittest
from pathlib import Path

import yaml

from ml.policy.policy_gate import PolicyContractError, evaluate_policy
from tools.audit.integrity_evidence import IntegrityEvidence

POLICY_PATH = Path("ml/policy/future_research_policy.example.yaml")


def evidence(status="passed"):
    ids = ["candidate_hash", "feature_schema_hash", "source_provenance", "marker_intervals", "aggregation_reproduction", "environment_application", "prediction_lock"]
    return {name: IntegrityEvidence(name, status, "fixture_evidence", {}) for name in ids}


def context():
    return {"metrics": {"macro_f1": .8}, "per_class_recall": {name: .5 for name in ["benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]},
            "flags": {"no_fit": True, "no_threshold_tuning": True, "no_row_exclusion": True}}


class TestFuturePolicyGate(unittest.TestCase):
    def setUp(self): self.policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))

    def test_every_yaml_rule_is_evaluated_and_participates(self):
        result = evaluate_policy(self.policy, context(), evidence())
        self.assertEqual(set(result["rules"]), set(self.policy["rules"])); self.assertTrue(result["coverage"]["passed"])
        self.assertTrue(result["passed"]); self.assertFalse(result["backend_integration_allowed"]); self.assertFalse(result["production_ready"])

    def test_not_executed_integrity_cannot_pass(self):
        checks = evidence(); checks["aggregation_reproduction"] = IntegrityEvidence("aggregation_reproduction", "not_executed", "secure_artifacts_unavailable", {})
        result = evaluate_policy(self.policy, context(), checks)
        self.assertFalse(result["passed"]); self.assertEqual(result["status"], "not_executed")

    def test_zero_recall_checks_every_supported_class(self):
        values = context(); values["per_class_recall"]["web_probe"] = 0
        result = evaluate_policy(self.policy, values, evidence())
        rule = result["rules"]["no_zero_recall_supported_class"]
        self.assertFalse(rule["passed"]); self.assertEqual(rule["zero_recall_classes"], ["web_probe"])

    def test_missing_class_is_not_executed_not_passed(self):
        values = context(); del values["per_class_recall"]["benign"]
        rule = evaluate_policy(self.policy, values, evidence())["rules"]["no_zero_recall_supported_class"]
        self.assertEqual(rule["status"], "not_executed"); self.assertFalse(rule["passed"])

    def test_unknown_rule_kind_is_rejected(self):
        self.policy["rules"]["bad"] = {"kind": "assert_true"}
        with self.assertRaises(PolicyContractError): evaluate_policy(self.policy, context(), evidence())


if __name__ == "__main__": unittest.main()
