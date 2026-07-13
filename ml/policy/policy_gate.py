"""Complete YAML-driven policy evaluator with integrity as a hard gate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.audit.integrity_evidence import IntegrityEvidence, final_integrity_gate


class PolicyContractError(ValueError):
    pass


def _compare(actual: float, operator: str, expected: float) -> bool:
    if operator == "gte": return actual >= expected
    if operator == "lte": return actual <= expected
    if operator == "gt": return actual > expected
    if operator == "lt": return actual < expected
    if operator == "eq": return actual == expected
    raise PolicyContractError(f"unsupported policy operator: {operator}")


def evaluate_policy(policy: dict[str, Any], context: dict[str, Any], integrity: dict[str, IntegrityEvidence]) -> dict[str, Any]:
    """Evaluate every declared rule; omission and not-executed evidence fail."""
    if policy.get("schema_version") != 1 or not isinstance(policy.get("rules"), dict):
        raise PolicyContractError("unsupported or missing policy schema")
    results: dict[str, dict[str, Any]] = {}
    for rule_id, rule in policy["rules"].items():
        kind = rule.get("kind")
        if kind == "metric":
            metric = str(rule["metric"])
            if metric not in context.get("metrics", {}):
                results[rule_id] = {"status": "not_executed", "passed": False, "reason": "metric_unavailable"}
            else:
                actual = float(context["metrics"][metric]); expected = float(rule["value"])
                passed = _compare(actual, str(rule["operator"]), expected)
                results[rule_id] = {"status": "passed" if passed else "failed", "passed": passed,
                                    "reason": "threshold_satisfied" if passed else "threshold_not_satisfied",
                                    "metric": metric, "actual": actual, "operator": rule["operator"], "expected": expected}
        elif kind == "integrity":
            check_id = str(rule["check_id"]); evidence = integrity.get(check_id)
            if evidence is None:
                results[rule_id] = {"status": "not_executed", "passed": False, "reason": "integrity_evidence_unavailable"}
            else:
                results[rule_id] = {"status": evidence.status, "passed": evidence.passed, "reason": evidence.reason}
        elif kind == "zero_recall":
            supported = list(policy.get("supported_classes") or [])
            recalls = context.get("per_class_recall", {})
            missing = sorted(set(supported) - set(recalls))
            zero = sorted(name for name in supported if name in recalls and float(recalls[name]) <= 0)
            status = "not_executed" if missing else ("failed" if zero else "passed")
            results[rule_id] = {"status": status, "passed": status == "passed",
                                "reason": "class_recall_unavailable" if missing else ("zero_recall_class" if zero else "all_supported_classes_have_positive_recall"),
                                "supported_class_count": len(supported), "missing_classes": missing, "zero_recall_classes": zero}
        elif kind == "boolean":
            field = str(rule["field"])
            if field not in context.get("flags", {}):
                results[rule_id] = {"status": "not_executed", "passed": False, "reason": "flag_unavailable"}
            else:
                passed = bool(context["flags"][field]) is bool(rule.get("expected", True))
                results[rule_id] = {"status": "passed" if passed else "failed", "passed": passed,
                                    "reason": "flag_matches" if passed else "flag_mismatch", "field": field}
        else:
            raise PolicyContractError(f"rule {rule_id!r} has unsupported kind {kind!r}")
    declared, evaluated = set(policy["rules"]), set(results)
    coverage = {"declared_rule_count": len(declared), "evaluated_rule_count": len(evaluated),
                "missing_rules": sorted(declared - evaluated), "unexpected_rules": sorted(evaluated - declared),
                "passed": declared == evaluated}
    integrity_gate = final_integrity_gate(integrity.values())
    rules_passed = coverage["passed"] and bool(results) and all(item["passed"] for item in results.values())
    passed = rules_passed and integrity_gate["passed"]
    status = "passed" if passed else ("not_executed" if any(item["status"] == "not_executed" for item in results.values()) or integrity_gate["status"] == "not_executed" else "failed")
    return {"status": status, "passed": passed, "rules": results, "coverage": coverage,
            "integrity_gate": integrity_gate, "backend_integration_allowed": passed and bool(policy.get("may_authorize_backend_integration", False)),
            "shadow_mode_allowed": passed and bool(policy.get("may_authorize_shadow_mode", False)),
            "production_ready": False}
