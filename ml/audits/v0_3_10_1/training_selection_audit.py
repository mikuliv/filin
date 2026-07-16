"""Post-hoc аудит 101 frozen training-policy записей без fit и predict."""
from __future__ import annotations

import math


def _close(left, right, tolerance=1e-12):
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_close(left[k], right[k], tolerance) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_close(a, b, tolerance) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
    return left == right


def policy_gates(record: dict, closed: dict, burden: dict) -> dict:
    w, e = record["window_metrics"], record["episode_metrics"]
    gates = {
        "closed_set": closed["macro_f1"] >= .90 and closed["balanced_accuracy"] >= .92
        and closed["benign_recall"] >= .92 and closed["FPR"] <= .08
        and closed["attack_macro_recall"] >= .92 and not closed.get("zero_recall_classes"),
        "strong_path": record["strong_alert_precision"] >= .97
        and record["strong_attack_window_recall"] >= .35
        and record["strong_benign_false_promotion_rate"] <= .02,
        "candidate_evidence": record["true_class_candidate_evidence_recall"] >= .92
        and min(record["per_class_candidate_evidence_recall"].values()) >= .85,
        "benign": w["benign_recall"] >= .90 and w["benign_window_alert_emission_rate"] <= .05
        and e["benign_episode_false_alert_rate"] <= .05
        and e["benign_episode_high_severity_alert_rate"] <= .03,
        "review": w["review_rate"] <= .15 and w["attack_review_rate"] <= .15,
        "episode": e["attack_episode_recall"] >= .97 and e["episode_alert_precision"] >= .95
        and e["attack_episode_unresolved_rate"] <= .03 and e["detection_by_second_window"] >= .92
        and (e["time_to_first_alert"]["median"] or 99) <= 2
        and (e["time_to_first_alert"]["maximum"] or 99) <= 3
        and min(v["recall"] for v in e["per_class"].values()) >= .90
        and not e.get("zero_recall_attack_episode_classes"),
        "legacy_pending": w["pending_rate"] <= .20 and w["attack_pending_rate"] <= .20,
        "burden_pending": burden["burden_pending_rate"] <= .20
        and burden["attack_burden_pending_rate"] <= .20,
    }
    return gates


def audit(evaluation: dict, original_records: list[dict], closed: dict, selected_policy_id: str) -> dict:
    if len(evaluation["results"]) != 101 or len(original_records) != 101:
        raise ValueError("Ожидалось ровно 101 policy record")
    reproduced, only_legacy_failed, burden_passed = 0, [], []
    selected_unchanged = False
    rows = []
    for evaluated, original in zip(evaluation["results"], original_records):
        exact = _close(evaluated["metrics"], original)
        reproduced += int(exact)
        gates = policy_gates(evaluated["metrics"], closed, evaluated["burden_aware"])
        non_pending = all(gates[k] for k in ("closed_set", "strong_path", "candidate_evidence", "benign", "review", "episode"))
        if non_pending and not gates["legacy_pending"]:
            only_legacy_failed.append(evaluated["evaluation_id"])
        if non_pending and gates["burden_pending"]:
            burden_passed.append(evaluated["evaluation_id"])
        if original["policy_id"] == selected_policy_id and exact:
            selected_unchanged = True
        rows.append({"evaluation_id": evaluated["evaluation_id"], "policy_id": original["policy_id"],
                     "original_metrics_reproduced": exact, "gates": gates,
                     "burden_aware": evaluated["burden_aware"]})
    return {
        "policy_count": 101, "reproduced_policy_count": reproduced,
        "all_original_metrics_reproduced": reproduced == 101,
        "candidates_passing_except_legacy_pending_count": len(only_legacy_failed),
        "candidates_passing_except_legacy_pending": only_legacy_failed,
        "candidates_passing_burden_aware_pending_count": len(burden_passed),
        "candidates_passing_burden_aware_pending": burden_passed,
        "selected_policy_id": selected_policy_id,
        "original_candidate_unchanged": selected_unchanged,
        "official_selection_changed": False,
        "records": rows,
    }
