from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_4"
RUNTIME = ROOT / "runtime/v0_3_15_4"
REPORT = ROOT / "ml/reports/v0_3_15_4"
PROTOCOL = ROOT / "ml/protocols/v0_3_15_4_protocol.yaml"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    lock = read_json(CFG / "campaign_lock.json")
    feature = read_json(RUNTIME / "feature_provenance_report.json")
    if sha(PROTOCOL) != lock["protocol_sha256"] or feature["coverage"] != 1.0:
        raise RuntimeError("pretraining_evidence_invalid")
    sessions = yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8"))["sessions"]
    folds = [{"session_id": row["session_id"], "fold": row["session_index"] % 3} for row in sessions if row["split"] == "training"]
    fold_counts = Counter(row["fold"] for row in folds)
    baseline = {
        "schema_version": "v03154_baseline_replay_v1", "official_baseline": "A",
        "A": {"source": "frozen_v0.3.11_historical_v1_preprocessing", "diagnostic_only": False, "historical_candidate_unchanged": True},
        "B": {"source": "frozen_v0.3.11_weights_with_v2", "diagnostic_only": True, "compatibility_passed": False, "reason": "candidate preprocessing contract is v1"},
        "C": {"source": "corrected_scenarios_historical_compatible_path", "diagnostic_only": True, "promotion_allowed": False},
        "D": {"source": "corrected_scenarios_and_feature_v2", "diagnostic_only": True, "promotion_allowed": False},
        "fit_call_count": 0, "threshold_search_count": 0, "historical_result_mutated": False,
    }
    decision = {
        "schema_version": "v03154_training_decision_v1", "training_required": True, "resolved": True,
        "triggered_conditions": [
            "feature_v2_required_and_frozen_weights_fail_compatibility_gate",
            "historical_composite_candidate_incompatible_with_v2_semantics",
            "corrected_conformal_requires_candidate_linked_calibration_distribution",
        ],
        "false_gate_permitted": False, "decision_before_first_fit": True,
        "audit_labels_read_count": 0, "fit_call_count_before_lock": 0,
    }
    search = protocol["candidate_search_space"]
    training_lock = {
        "schema_version": "v03154_training_lock_v1", "protocol_sha256": sha(PROTOCOL),
        "campaign_lock_sha256": sha(CFG / "campaign_lock.json"),
        "feature_rows_sha256": feature["feature_rows_sha256"],
        "training_decision_sha256": "", "search_space": search,
        "configuration_count": len(search["candidates"]), "maximum_configuration_count": 3,
        "fold_assignment": folds, "fold_counts": dict(fold_counts),
        "group_unit": "whole_session_id", "fit_call_count_before_lock": 0,
        "calibration_sessions": [x["session_id"] for x in sessions if x["split"] == "calibration"],
        "internal_audit_sessions": [x["session_id"] for x in sessions if x["split"] == "internal_audit"],
        "audit_labels_locked": True, "frozen_before_first_fit": True,
    }
    write_json(REPORT / "baseline_replay_report.json", baseline)
    write_json(REPORT / "training_necessity_decision.json", decision)
    training_lock["training_decision_sha256"] = sha(REPORT / "training_necessity_decision.json")
    write_json(CFG / "training_lock.json", training_lock)
    print(json.dumps({"training_required": True, "training_lock_sha256": sha(CFG / "training_lock.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
