from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_4_7_3"
CONTRACTS = ROOT / "lab_console/contracts/v0_4_7_3"


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    required = {
        "summary.md", "v0_4_7_3_policy_result.json", "role_assignments.json", "control_data_catalog.json",
        "control_pack_metadata.json", "scenario_novelty_assessment.json", "data_isolation_report.json", "blindness_report.json",
        "criterion_lineage_map.json", "label_commitment_metadata.json", "prediction_plan.json", "active_inference_record.json",
        "proposal_inference_record.json", "inference_recovery_record.json", "prediction_commitments.json", "label_unlock_record.json",
        "evaluation_bundle.json", "comparability_assessment.json", "comparison_bundle.json", "previous_failure_resolution_assessment.json",
        "blind_acceptance_gate.json", "manual_review.json", "final_decision.json", "positive_campaign.json", "negative_campaign.json",
        "claim_evidence_ledger.json", "test_report.json", "browser_acceptance_report.md", "known_limitations.md",
        "v0_4_7_3_bundle_manifest.json", "v0_4_7_3_bundle_manifest.sha256", "v0_4_7_3_semantic.sha256",
    }
    errors.extend("missing_report:" + name for name in sorted(required) if not (REPORT / name).is_file())
    schemas = sorted(CONTRACTS.glob("*.schema.json"))
    if len(schemas) != 51: errors.append("contract_count_invalid")
    for path in schemas:
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False: errors.append("contract_not_strict:" + path.name)
        if schema.get("properties", {}).get("payload", {}).get("additionalProperties") is not False: errors.append("payload_not_strict:" + path.name)
    if not errors:
        manifest_path = REPORT / "v0_4_7_3_bundle_manifest.json"
        detached = (REPORT / "v0_4_7_3_bundle_manifest.sha256").read_text(encoding="ascii").split()[0]
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != detached: errors.append("bundle_manifest_sha_mismatch")
        for row in load("v0_4_7_3_bundle_manifest.json").get("entries", []):
            path = REPORT / row["path"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]: errors.append("bundle_entry_mismatch:" + row["path"])
    policy = load("v0_4_7_3_policy_result.json")
    expected = {
        "v0_4_7_3_procedure_passed": True, "internal_blind_validation_passed": False,
        "final_decision": "failed_validation", "next_allowed_stage": "v0.4.7.4", "v0_4_8_allowed": False,
        "active_candidate_unchanged": True, "proposal_unchanged": True, "old_proposal_unchanged": True,
        "candidate_registry_unchanged": True, "backend_tree_unchanged": True, "protected_file_changed_count": 0,
        "data_isolation_gate_status": "passed", "blindness_gate_status": "passed", "comparability_status": "comparable",
        "predictions_created_before_unlock": True, "deterministic_evaluation_rebuild_passed": True,
        "pre_unlock_label_access_count": 0, "invalid_label_unlock_count": 0, "post_unlock_official_inference_count": 0,
        "missing_prediction_count": 0, "duplicate_prediction_count": 0, "invalid_prediction_count": 0,
        "candidate_registration_count": 0, "automatic_promotion_count": 0, "active_candidate_change_count": 0,
        "winner_selection_count": 0, "real_data_input_count": 0, "personal_data_input_count": 0,
        "external_network_attempt_count": 0, "shell_execution_count": 0, "push_performed": False,
    }
    for key, value in expected.items():
        if policy.get(key) != value: errors.append("invalid_policy_value:" + key)
    minimums = {"session_count": 36, "source_object_count": 6480, "scored_window_count": 6000,
                "criterion_lineage_source_count": 48, "acceptance_criterion_count": 48, "previous_failure_count": 6,
                "prediction_commitment_count": 2, "completed_manual_review_count": 1,
                "positive_scenario_passed_count": 150, "negative_scenario_rejected_count": 260}
    for key, value in minimums.items():
        if policy.get(key, 0) < value: errors.append("minimum_not_met:" + key)
    if load("scenario_novelty_assessment.json").get("status") != "passed": errors.append("novelty_failed")
    if load("data_isolation_report.json").get("status") != "passed": errors.append("isolation_failed")
    if load("blindness_report.json").get("status") != "passed": errors.append("blindness_failed")
    if not load("inference_recovery_record.json").get("result_identical_to_uninterrupted_reference"): errors.append("recovery_not_reproducible")
    if len(load("prediction_commitments.json")) != 2 or load("label_unlock_record.json").get("prediction_commitment_count") != 2: errors.append("commitment_order_invalid")
    decision = load("final_decision.json")
    if decision.get("decision") != "failed_validation" or decision.get("v0_4_8_allowed") is not False or not decision.get("v0_4_7_3_procedure_passed"): errors.append("decision_invalid")
    if load("comparability_assessment.json").get("status") != "comparable": errors.append("comparability_invalid")
    if len(load("positive_campaign.json")) < 150 or len(load("negative_campaign.json")) < 260: errors.append("campaign_size_invalid")
    registry = ROOT / "collectors/shadow/contracts/candidate_registry_v1.json"
    if hashlib.sha256(registry.read_bytes()).hexdigest() != "31aa0d7ecf4d9134bd379bae4cd16392d330e8ef3c765098406cce069898dc9d": errors.append("candidate_registry_changed")
    if subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip() != "04218a4eb01534950efd5f7d6390f1a575cacbc8": errors.append("backend_tree_changed")
    result = {"schema_version": "v0_4_7_3_standalone_verification_v1", "passed": not errors, "errors": errors,
              "contract_count": len(schemas), "sessions": policy.get("session_count"), "scored_windows": policy.get("scored_window_count"),
              "decision": policy.get("final_decision"), "resolved_previous_failures": policy.get("resolved_previous_failure_count"),
              "positive_passed": policy.get("positive_scenario_passed_count"), "negative_rejected": policy.get("negative_scenario_rejected_count")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())
