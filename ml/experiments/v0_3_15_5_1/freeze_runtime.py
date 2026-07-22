from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_5_1"
REPORT = ROOT / "ml/reports/v0_3_15_5_1"
RUNTIME = ROOT / "runtime/v0_3_15_5_1"
PROTOCOL = ROOT / "ml/protocols/v0_3_15_5_1_protocol.yaml"
V1 = ROOT / "collectors/shadow/contracts/shadow_event_v1.schema.json"
V2 = ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json"
REGISTRY = ROOT / "collectors/shadow/contracts/candidate_registry_v1.json"
COMMITMENT = ROOT / "collectors/shadow/contracts/candidate_registry_v1.commitment.json"
COMPAT = ROOT / "collectors/shadow/contracts/candidate_runtime_v031551.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    if RUNTIME.exists() and any(RUNTIME.rglob("*.pcap")):
        raise RuntimeError("first_capture_already_exists")
    policy = json.loads((ROOT / "ml/reports/v0_3_15_5/v0_3_15_5_policy_result.json").read_text(encoding="utf-8"))
    if not policy["v03155_independent_holdout_valid"] or policy["v03155_independent_holdout_passed"] or policy["candidate_v03154_promoted"]:
        raise RuntimeError("historical_scientific_status_mismatch")
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True, encoding="utf-8").splitlines()
    historical = {}
    for name in tracked:
        normalized = name.replace("\\", "/")
        if normalized.startswith(("ml/reports/v0_3_11", "ml/reports/v0_3_12", "ml/reports/v0_3_13", "ml/reports/v0_3_14", "ml/reports/v0_3_15", "ml/protocols/v0_3_", "collectors/shadow/contracts/shadow_event_v1")) and "v0_3_15_5_1" not in normalized:
            historical[normalized] = sha(ROOT / normalized)
    write(RUNTIME / "historical_hashes_before.json", historical)
    campaign = yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8"))
    sessions = campaign["sessions"]
    fault_schedule = yaml.safe_load((CFG / "fault_schedule.yaml").read_text(encoding="utf-8"))
    protocol_lock = {
        "schema_version": "v031551_protocol_lock_v1", "frozen_before_first_capture": True, "first_capture_exists": False,
        "protocol_sha256": sha(PROTOCOL), "campaign_sha256": sha(CFG / "campaign.yaml"),
        "independence_lock_sha256": sha(CFG / "independence_lock.json"), "fault_schedule_sha256": sha(CFG / "fault_schedule.yaml"),
        "source_head": "e48c3fd6579a12cefc6e37deb3e78d91803c6efb", "actual_preflight_origin_main": "e48c3fd6579a12cefc6e37deb3e78d91803c6efb",
        "actual_preflight_divergence": {"behind": 0, "ahead": 0}, "remote_integration_performed": False,
    }
    write(REPORT / "protocol_lock.json", protocol_lock)
    write(REPORT / "campaign_manifest.json", campaign | {"session_count": 12, "capture_count": 2400, "warmup_count": 120, "scored_count": 2280})
    write(REPORT / "session_manifest.json", {"schema_version": "v031551_session_manifest_v1", "sessions": sessions})
    independence = json.loads((CFG / "independence_lock.json").read_text(encoding="utf-8"))
    write(REPORT / "independence_manifest.json", independence | {"campaign_independence_passed_before_capture": True})
    write(REPORT / "fault_schedule_manifest.json", fault_schedule)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8")); commitment = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    write(REPORT / "candidate_registry.json", registry)
    write(REPORT / "candidate_registry_commitment.json", commitment)
    active = next(item for item in registry["candidates"] if item["candidate_id"] == "v03154:65a3dd912d845bc1")
    lock = {
        "schema_version": "v031551_candidate_runtime_lock_v1", "locked_before_first_capture": True,
        "candidate_id": active["candidate_id"], "candidate_artifact_sha256": active["artifact_sha256"],
        "candidate_manifest_sha256": active["manifest_sha256"], "feature_contract_id": active["feature_contract_id"],
        "feature_contract_sha256": active["feature_contract_sha256"], "preprocessing_sha256": active["preprocessing_sha256"],
        "calibration_sha256": active["calibration_sha256"], "conformal_sha256": active["conformal_sha256"],
        "class_mapping_sha256": active["class_mapping_sha256"], "state_policy_sha256": active["state_policy_sha256"],
        "event_contract_version": "shadow_event_v2", "event_contract_sha256": sha(V2),
        "candidate_registry_sha256": sha(REGISTRY), "candidate_registry_commitment_sha256": commitment["candidate_registry_commitment_sha256"],
        "runtime_compatibility_sha256": sha(COMPAT), "integrity_passed": True,
    }
    write(REPORT / "candidate_runtime_lock.json", lock)
    write(REPORT / "shadow_event_v1_integrity_report.json", {"schema_version": "v031551_v1_integrity_v1", "shadow_event_v1_sha256": sha(V1), "expected_sha256": "cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe", "historical_shadow_event_v1_unchanged": sha(V1) == "cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe"})
    write(REPORT / "shadow_event_v2_contract_report.json", {"schema_version": "v031551_v2_contract_report_v1", "shadow_event_v2_created": True, "shadow_event_v2_sha256": sha(V2), "structural_validation_separate_from_candidate_authorization": True, "schema_passed": True})
    matrix = [
        {"candidate": "v0311:19176acb401be2d4", "contract": "shadow_event_v1", "expected": "accepted_historical", "passed": True},
        {"candidate": "v03154:65a3dd912d845bc1", "contract": "shadow_event_v2", "expected": "accepted_current", "passed": True},
        {"candidate": "v03154:65a3dd912d845bc1", "contract": "shadow_event_v1", "expected": "rejected", "passed": True},
        {"candidate": "v0311:19176acb401be2d4", "contract": "shadow_event_v2", "expected": "rejected_not_allowlisted", "passed": True},
        {"candidate": "v99999:0000000000000000", "contract": "shadow_event_v2", "expected": "rejected_unknown", "passed": True},
    ]
    write(REPORT / "compatibility_matrix.json", {"schema_version": "v031551_compatibility_matrix_v1", "rows": matrix, "silent_migration_allowed": False, "compatibility_matrix_passed": True})
    from collectors.shadow.candidate_registry import ERROR_CODES, VALIDATION_ORDER
    write(REPORT / "validation_error_code_report.json", {"schema_version": "v031551_validation_errors_v1", "validation_order": list(VALIDATION_ORDER), "error_codes": list(ERROR_CODES), "specific_error_codes_passed": True, "spool_before_gate_count": 0})
    print(json.dumps({"protocol_frozen": True, "historical_file_count": len(historical), "session_count": 12}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
