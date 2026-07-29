from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_7_2"
CONTRACTS = ROOT / "lab_console" / "contracts" / "v0_4_7_2"


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    required = {
        "summary.md", "v0_4_7_2_policy_result.json", "data_catalog.json", "data_isolation_report.json",
        "split_manifest.json", "training_recipe.json", "training_runs.json", "reproducibility_assessment.json",
        "model_semantic_fingerprint.json", "proposal_manifest.json", "internal_screening_result.json",
        "corrective_gate_result.json", "comparison_bundle.json", "failure_correction_assessment.json",
        "manual_review.json", "final_decision.json", "test_report.json", "browser_acceptance_report.md",
        "v0_4_7_2_bundle_manifest.json", "v0_4_7_2_bundle_manifest.sha256", "v0_4_7_2_semantic.sha256",
        "known_limitations.md",
    }
    errors.extend("missing_report:" + name for name in sorted(required) if not (REPORT / name).is_file())
    schemas = sorted(CONTRACTS.glob("*.schema.json"))
    if len(schemas) != 36:
        errors.append("contract_count_invalid")
    for path in schemas:
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            errors.append("contract_not_strict:" + path.name)
        if schema.get("properties", {}).get("payload", {}).get("additionalProperties") is not False:
            errors.append("payload_not_strict:" + path.name)

    if not errors:
        manifest_path = REPORT / "v0_4_7_2_bundle_manifest.json"
        manifest = load("v0_4_7_2_bundle_manifest.json")
        detached = (REPORT / "v0_4_7_2_bundle_manifest.sha256").read_text(encoding="ascii").split()[0]
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != detached:
            errors.append("bundle_manifest_sha_mismatch")
        for row in manifest.get("entries", []):
            path = REPORT / row["path"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                errors.append("bundle_entry_mismatch:" + row["path"])

    policy = load("v0_4_7_2_policy_result.json")
    expected = {
        "old_proposal_unchanged": True, "active_candidate_unchanged": True,
        "candidate_registry_unchanged": True, "backend_tree_unchanged": True,
        "protected_file_changed_count": 0, "real_data_input_count": 0, "personal_data_input_count": 0,
        "old_blind_pack_object_reuse_count": 0, "old_blind_pack_session_reuse_count": 0,
        "old_blind_pack_seed_reuse_count": 0, "data_isolation_gate_status": "passed",
        "screening_unlocked_before_freeze_count": 0, "new_critical_regression_count": 0,
        "candidate_registration_count": 0, "automatic_promotion_count": 0, "active_candidate_change_count": 0,
        "external_validation_claim": False, "independent_validation_claim": False,
        "v0_4_8_allowed": False, "model_binary_committed_count": 0, "push_performed": False,
        "admitted_to_new_blind_validation": True, "v0_4_7_3_allowed": True,
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            errors.append("invalid_policy_value:" + key)
    minimums = {
        "new_session_count": 48, "new_object_count": 5760, "completed_training_execution_count": 3,
        "interrupted_training_execution_count": 1, "recovered_training_execution_count": 1,
        "corrective_criterion_count": 24, "passed_corrective_criterion_count": 24,
        "corrected_previous_failure_count": 6, "active_comparison_count": 1,
        "previous_proposal_comparison_count": 1, "completed_manual_review_count": 1,
        "positive_scenario_passed_count": 130, "negative_scenario_rejected_count": 220,
        "browser_acceptance_count": 30,
    }
    for key, value in minimums.items():
        if policy.get(key, 0) < value:
            errors.append("minimum_not_met:" + key)

    runs = load("training_runs.json").get("runs", [])
    completed = [row for row in runs if row.get("status") == "completed"]
    if len(completed) != 3 or len({row.get("model_semantic_sha256") for row in completed}) != 1:
        errors.append("training_reproducibility_invalid")
    if not any(row.get("status") == "interrupted" for row in runs) or not any(row.get("recovered") for row in runs):
        errors.append("recovery_evidence_missing")
    if load("reproducibility_assessment.json").get("status") == "not_reproducible":
        errors.append("training_not_reproducible")
    proposal = load("representative_proposal.json")
    if "candidate_id" in proposal or not proposal.get("frozen"):
        errors.append("proposal_identity_or_freeze_invalid")
    if not proposal.get("proposal_id", "").startswith("proposal:v0472:"):
        errors.append("proposal_namespace_invalid")
    gate = load("corrective_gate_result.json")
    if not gate.get("all_mandatory_passed") or len(gate.get("results", [])) != 24 or not all(row.get("status") == "passed" for row in gate.get("results", [])):
        errors.append("corrective_gate_failed")

    registry = ROOT / "collectors/shadow/contracts/candidate_registry_v1.json"
    if hashlib.sha256(registry.read_bytes()).hexdigest() != "31aa0d7ecf4d9134bd379bae4cd16392d330e8ef3c765098406cce069898dc9d":
        errors.append("candidate_registry_changed")
    backend = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip()
    if backend != "04218a4eb01534950efd5f7d6390f1a575cacbc8":
        errors.append("backend_tree_changed")
    old_frozen = ROOT / "ml/reports/v0_4_7/v0_4_7_bundle_manifest.json"
    if hashlib.sha256(old_frozen.read_bytes()).hexdigest() != "60dfa9ad7ffdb7b93e43e4d8e0f261f3165cef031dcef4a4bf8620e1be17c8d1":
        errors.append("v0_4_7_changed")

    result = {
        "schema_version": "v0_4_7_2_standalone_verification_v1", "passed": not errors, "errors": errors,
        "contract_count": len(schemas), "sessions": policy.get("new_session_count"), "objects": policy.get("new_object_count"),
        "training_reproducibility": policy.get("training_reproducibility_status"),
        "decision": policy.get("final_decision"), "positive_passed": policy.get("positive_scenario_passed_count"),
        "negative_rejected": policy.get("negative_scenario_rejected_count"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
