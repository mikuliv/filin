from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_4_7"
CONTRACTS = ROOT / "lab_console/contracts/v0_4_7"


def main() -> int:
    errors: list[str] = []
    policy = json.loads((REPORT / "v0_4_7_policy_result.json").read_text(encoding="utf-8"))
    manifest_path = REPORT / "v0_4_7_bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = (REPORT / "v0_4_7_bundle_manifest.sha256").read_text(encoding="ascii").split()[0]
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != expected: errors.append("bundle_manifest_sha_mismatch")
    for item in manifest["entries"]:
        path = REPORT / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]: errors.append("bundle_file_mismatch:" + item["path"])
    schemas = sorted(CONTRACTS.glob("*.schema.json"))
    if len(schemas) != 45: errors.append("contract_count_invalid")
    for path in schemas:
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False: errors.append("contract_not_strict:" + path.name)
    expected_values = {
        "session_count": lambda x: x >= 20, "capture_count": lambda x: x >= 4000, "scored_window_count": lambda x: x >= 3800,
        "overlap_gate_status": lambda x: x == "passed", "blindness_gate_status": lambda x: x == "passed",
        "prediction_commitment_count": lambda x: x == 2, "evaluation_rebuild_deterministic": bool,
        "comparability_status": lambda x: x == "comparable", "final_decision": lambda x: x == "failed_validation",
        "review_independence_status": lambda x: x == "role_separated_blind", "positive_scenario_passed_count": lambda x: x >= 130,
        "negative_scenario_passed_count": lambda x: x >= 230,
    }
    for key, predicate in expected_values.items():
        if not predicate(policy.get(key)): errors.append("invalid_policy_value:" + key)
    zero = ["overlap_count", "label_package_mutation_count", "pre_unlock_label_access_count", "test_oracle_access_count",
            "prediction_package_mutation_count", "invalid_label_unlock_count", "post_unlock_official_inference_count",
            "candidate_registration_count", "active_candidate_change_count"]
    for key in zero:
        if policy.get(key) != 0: errors.append("required_zero:" + key)
    for key in ("passed_for_registration_review", "independent_blind_validation_passed", "v0_4_8_allowed", "winner_selected", "production_ready", "external_validation_claim"):
        if policy.get(key) is not False: errors.append("required_false:" + key)
    registry = ROOT / "collectors/shadow/contracts/candidate_registry_v1.json"
    if hashlib.sha256(registry.read_bytes()).hexdigest() != "31aa0d7ecf4d9134bd379bae4cd16392d330e8ef3c765098406cce069898dc9d": errors.append("candidate_registry_changed")
    backend = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip()
    if backend != "04218a4eb01534950efd5f7d6390f1a575cacbc8": errors.append("backend_tree_changed")
    forbidden_suffixes = {".joblib", ".pkl", ".sqlite", ".sqlite3", ".pcap", ".parquet"}
    if any(path.suffix.lower() in forbidden_suffixes for path in REPORT.rglob("*")): errors.append("forbidden_runtime_artifact_in_report")
    result = {"schema_version": "v0_4_7_standalone_verification_v1", "passed": not errors, "errors": errors,
              "contract_count": len(schemas), "positive_passed": policy.get("positive_scenario_passed_count"),
              "negative_rejected": policy.get("negative_scenario_passed_count"), "decision": policy.get("final_decision"),
              "scientific_gate_passed": policy.get("blind_acceptance_gate_passed")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())
