from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_6"
CONTRACTS = ROOT / "lab_console" / "contracts" / "v0_4_6"
START = "665ab1207de034c90aef74cb28efd9b1db704dc9"


def main() -> int:
    errors = []
    policy = json.loads((REPORT / "v0_4_6_policy_result.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPORT / "v0_4_6_bundle_manifest.json").read_text(encoding="utf-8"))
    expected_manifest = (REPORT / "v0_4_6_bundle_manifest.sha256").read_text(encoding="ascii").strip()
    actual_manifest = hashlib.sha256((REPORT / "v0_4_6_bundle_manifest.json").read_bytes()).hexdigest()
    if expected_manifest != actual_manifest: errors.append("bundle_manifest_sha_mismatch")
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]: errors.append("bundle_file_mismatch:" + item["path"])
    schemas = sorted(CONTRACTS.glob("*.schema.json"))
    if len(schemas) != 40: errors.append("contract_count_invalid")
    for path in schemas:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("additionalProperties") is not False or value.get("type") != "object": errors.append("contract_not_strict:" + path.name)
    required_true = ["active_candidate_identity_unchanged", "active_candidate_artifact_unchanged", "candidate_registry_unchanged", "backend_tree_unchanged", "data_provenance_complete", "admission_gate_definition_frozen", "proposal_manifest_validation_passed", "proposal_semantic_hash_validation_passed"]
    required_false = ["candidate_registration_allowed", "active_candidate_change_allowed", "external_trial_execution_allowed", "public_deployment_allowed", "backend_integration_allowed", "production_ready", "automatic_response_ready", "push_performed", "all_distribution_profiles_ready"]
    zero = ["protected_file_changed_count", "real_data_input_count", "personal_data_input_count", "overlap_failure_count", "test_oracle_access_count", "blind_label_access_count", "not_reproducible_training_count", "duplicate_active_artifact_proposal_count", "screening_unlocked_before_freeze_count", "candidate_registration_count", "automatic_promotion_count", "active_candidate_change_count", "candidate_registry_change_count", "hidden_weight_count", "winner_selection_count", "post_screening_training_count", "post_screening_threshold_change_count", "source_artifact_mutation_count", "source_semantic_sha_changed_count", "arbitrary_command_endpoint_count", "shell_execution_count", "external_network_attempt_count", "model_upload_count", "dataset_upload_count", "model_binary_committed_count", "dataset_committed_count"]
    for key in required_true:
        if policy.get(key) is not True: errors.append("required_true:" + key)
    for key in required_false:
        if policy.get(key) is not False: errors.append("required_false:" + key)
    for key in zero:
        if policy.get(key) != 0: errors.append("required_zero:" + key)
    if policy.get("positive_scenario_passed_count", 0) < 110: errors.append("positive_campaign_too_small")
    if policy.get("negative_scenario_rejected_count", 0) < 190: errors.append("negative_campaign_too_small")
    if policy.get("completed_training_execution_count", 0) < 2 or policy.get("proposal_count") != 1: errors.append("official_campaign_incomplete")
    if policy.get("reuse_coverage_percent") != 100: errors.append("reuse_coverage_invalid")
    registry = ROOT / "collectors" / "shadow" / "contracts" / "candidate_registry_v1.json"
    if hashlib.sha256(registry.read_bytes()).hexdigest() != "31aa0d7ecf4d9134bd379bae4cd16392d330e8ef3c765098406cce069898dc9d": errors.append("candidate_registry_changed")
    backend = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip()
    if backend != "04218a4eb01534950efd5f7d6390f1a575cacbc8": errors.append("backend_tree_changed")
    result = {"schema_version": "v0_4_6_standalone_verification_v1", "passed": not errors, "errors": errors, "contract_count": len(schemas),
              "positive_passed": policy.get("positive_scenario_passed_count"), "negative_rejected": policy.get("negative_scenario_rejected_count"),
              "training_executions": policy.get("training_execution_count"), "proposal_count": policy.get("proposal_count"), "decision_admitted": policy.get("proposal_admitted_to_separate_validation")}
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())
