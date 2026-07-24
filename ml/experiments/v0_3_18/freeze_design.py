"""Формирование frozen design policies v0.3.18."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_18"


def write(name: str, value: Any) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def role_matrix() -> dict[str, Any]:
    common_forbidden = [
        "change_candidate", "change_protocol_after_freeze", "change_thresholds",
        "external_network", "backend_call", "automatic_action",
    ]
    definitions = {
        "project_owner": {
            "allowed_actions": ["approve_protocol_before_freeze", "provide_candidate_identity"],
            "data_access": ["protocol", "candidate_commitment", "aggregate_results"],
            "labels_access_before_prediction_freeze": False,
            "predictions_access_before_prediction_freeze": False,
            "run_inference": False, "calculate_metrics": False,
            "change_protocol": False, "approve_result": False,
            "conflicting_roles": ["label_custodian", "independent_evaluator", "external_reviewer", "result_approver"],
        },
        "data_provider": {
            "allowed_actions": ["prepare_holdout", "prepare_dataset_manifest", "attest_provenance"],
            "data_access": ["inputs", "dataset_manifest"],
            "labels_access_before_prediction_freeze": False,
            "predictions_access_before_prediction_freeze": False,
            "run_inference": False, "calculate_metrics": False,
            "change_protocol": False, "approve_result": False,
            "conflicting_roles": ["trial_operator", "independent_evaluator", "result_approver"],
        },
        "trial_operator": {
            "allowed_actions": ["receive_blind_inputs", "run_frozen_inference", "freeze_predictions"],
            "data_access": ["inputs", "candidate_runtime", "prediction_namespace"],
            "labels_access_before_prediction_freeze": False,
            "predictions_access_before_prediction_freeze": True,
            "run_inference": True, "calculate_metrics": False,
            "change_protocol": False, "approve_result": False,
            "conflicting_roles": ["label_custodian", "independent_evaluator", "result_approver"],
        },
        "label_custodian": {
            "allowed_actions": ["create_label_commitment", "reveal_labels_after_prediction_freeze"],
            "data_access": ["labels", "label_commitment"],
            "labels_access_before_prediction_freeze": True,
            "predictions_access_before_prediction_freeze": False,
            "run_inference": False, "calculate_metrics": False,
            "change_protocol": False, "approve_result": False,
            "conflicting_roles": ["trial_operator", "independent_evaluator", "result_approver"],
        },
        "independent_evaluator": {
            "allowed_actions": ["verify_reveal", "calculate_frozen_metrics", "build_result"],
            "data_access": ["frozen_predictions", "revealed_labels", "metric_policy"],
            "labels_access_before_prediction_freeze": False,
            "predictions_access_before_prediction_freeze": False,
            "run_inference": False, "calculate_metrics": True,
            "change_protocol": False, "approve_result": False,
            "conflicting_roles": ["project_owner", "data_provider", "trial_operator", "label_custodian", "result_approver"],
        },
        "external_reviewer": {
            "allowed_actions": ["verify_manifests", "verify_hashes", "verify_roles", "verify_chronology"],
            "data_access": ["review_package", "reproducibility_package", "aggregate_results"],
            "labels_access_before_prediction_freeze": False,
            "predictions_access_before_prediction_freeze": False,
            "run_inference": False, "calculate_metrics": False,
            "change_protocol": False, "approve_result": False,
            "conflicting_roles": ["project_owner", "trial_operator", "result_approver"],
        },
        "result_approver": {
            "allowed_actions": ["record_pass_fail_or_invalidation", "finalize_result"],
            "data_access": ["review_findings", "aggregate_results", "chronology"],
            "labels_access_before_prediction_freeze": False,
            "predictions_access_before_prediction_freeze": False,
            "run_inference": False, "calculate_metrics": False,
            "change_protocol": False, "approve_result": True,
            "conflicting_roles": ["project_owner", "data_provider", "trial_operator", "label_custodian", "independent_evaluator", "external_reviewer"],
        },
    }
    for value in definitions.values():
        value["forbidden_actions"] = common_forbidden
    return {
        "schema_version": "v0318_role_separation_matrix_v1",
        "stage": "v0.3.18",
        "real_trial_requires_distinct_actors": True,
        "synthetic_rehearsal_namespaces_roles_separately": True,
        "role_attestation_contract": "external_trial_role_attestation_v1",
        "role_conflict_count": 0,
        "roles": definitions,
    }


def data_acceptance() -> dict[str, Any]:
    return {
        "schema_version": "v0318_data_acceptance_policy_v1",
        "stage": "v0.3.18",
        "status": "frozen",
        "supported_input_forms": ["pcap"],
        "unsupported_without_separate_implementation": ["netflow", "csv_features", "raw_event_rows"],
        "required": [
            "dataset_owner_pseudonym", "legal_basis_placeholder", "external_data_usage_mode",
            "capture_period", "source_environment_identity", "network_node_grouping",
            "episode_grouping", "class_taxonomy", "label_provenance",
            "label_creation_method", "anonymization_status", "payload_handling",
            "credential_exposure_check", "personal_data_check", "malware_check",
            "encryption_status", "transfer_method", "retention_period_placeholder",
            "deletion_requirements", "publication_restrictions", "overlap_attestation",
        ],
        "allowed_usage_modes": [
            "frozen_external_evaluation", "authorized_development",
            "synthetic_protocol_rehearsal",
        ],
        "usage_modes_mutually_exclusive": True,
        "independence_grouping": [
            "episode", "time_range", "network_node", "environment",
            "organization", "capture_origin",
        ],
        "row_random_split_proves_independence": False,
        "minimum_technical_quality": {
            "parseable_pcap": True, "stable_capture_origin": True,
            "nonempty_episode_manifest": True, "timestamps_present": True,
            "class_taxonomy_mapped_before_commitment": True,
        },
        "rejected_input_conditions": [
            "unsupported_format", "missing_provenance", "unclear_usage_right",
            "credential_finding", "prohibited_payload", "privacy_clearance_failed",
            "malware_clearance_failed", "manifest_mismatch", "detected_overlap",
            "unapproved_sample_plan",
        ],
    }


def contamination() -> dict[str, Any]:
    return {
        "schema_version": "v0318_contamination_policy_v1",
        "stage": "v0.3.18", "status": "frozen",
        "reference_sets": [
            "training", "calibration", "conformal", "threshold_selection",
            "internal_regression_fixtures", "previous_prospective_holdouts",
            "development_pcap", "generated_scenario_seeds", "known_scenario_templates",
        ],
        "checks": [
            "exact_file_hash", "normalized_capture_hash", "episode_identity",
            "session_fingerprint", "time_overlap", "node_overlap",
            "organization_overlap", "scenario_seed_overlap",
            "scenario_template_overlap", "duplicated_label_source",
        ],
        "different_filename_proves_independence": False,
        "unverifiable_check_result": "limitation_and_provider_attestation_required",
        "full_independence_claim_without_all_checks": False,
        "detected_overlap_action": "trial_invalidated",
    }


def blind_protocol() -> dict[str, Any]:
    return {
        "schema_version": "v0318_blind_holdout_protocol_v1",
        "stage": "v0.3.18", "status": "frozen",
        "steps": [
            "dataset_manifest", "label_commitment", "holdout_commitment",
            "candidate_commitment", "evaluator_commitment", "blind_input_handoff",
            "frozen_inference", "prediction_validation", "prediction_commitment",
            "label_reveal", "label_commitment_verification", "frozen_evaluation",
            "result_bundle", "external_review", "result_approval", "finalization",
        ],
        "label_reveal_requires_prediction_commitment": True,
        "post_reveal_prediction_change_allowed": False,
        "unauthorized_second_evaluation_allowed": False,
        "hash_commitment_is_signature": False,
        "canonicalization": "utf8_json_sorted_keys_compact",
        "digest_algorithm": "sha256",
    }


def metric_policy() -> dict[str, Any]:
    return {
        "schema_version": "v0318_metric_policy_v1",
        "stage": "v0.3.18", "status": "frozen",
        "class_taxonomy": ["benign", "auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"],
        "metrics": [
            "confusion_matrix", "per_class_precision", "per_class_recall",
            "per_class_f1", "macro_f1", "weighted_f1", "balanced_accuracy",
            "abstention_count", "abstention_rate", "coverage",
            "selective_accuracy", "missing_prediction_count",
            "duplicate_prediction_count", "invalid_prediction_count",
            "episode_level_metrics", "uncertainty_intervals", "dataset_composition",
        ],
        "false_positive_policy": "report_per_class_and_benign_as_attack_count",
        "false_negative_policy": "report_per_class_attack_as_benign_count",
        "abstention_is_correct": False,
        "missing_prediction_default_class": None,
        "post_hoc_threshold_selection_allowed": False,
        "post_reveal_class_merge_allowed": False,
        "post_hoc_averaging_selection_allowed": False,
        "unresolved_external_acceptance_thresholds": [
            "organization_specific_false_positive_limit",
            "organization_specific_false_negative_limit",
            "minimum_external_macro_f1",
        ],
        "threshold_resolution_rule": "must_be_agreed_before_holdout_commitment",
        "policy_complete_for_protocol_rehearsal": True,
        "policy_complete_for_real_trial_execution": False,
        "protocol_rehearsal_only": True,
        "scientific_evidence": False,
    }


def sufficiency_policy() -> dict[str, Any]:
    return {
        "schema_version": "v0318_sample_sufficiency_policy_v1",
        "stage": "v0.3.18", "status": "frozen",
        "required_review_fields": [
            "total_episodes", "episodes_per_class", "independent_capture_origins",
            "independent_time_ranges", "organization_or_environment_sources",
            "node_diversity", "class_imbalance", "confidence_interval_width",
            "abstention_coverage", "unsupported_classes",
        ],
        "decision_table": [
            {"condition": "missing_required_field", "decision": "reject_sample_plan"},
            {"condition": "single_episode_many_rows", "decision": "insufficient"},
            {"condition": "unsupported_class_present", "decision": "review_and_freeze_handling_before_commitment"},
            {"condition": "confidence_interval_plan_absent", "decision": "reject_sample_plan"},
            {"condition": "all_context_specific_minima_approved", "decision": "sample_plan_eligible"},
        ],
        "universal_numeric_minimum_defined": False,
        "reason": "Контекст внешнего источника ещё не согласован.",
        "approval_required_before_holdout_commitment": True,
    }


def stop_conditions() -> dict[str, Any]:
    conditions = [
        "labels_revealed_before_prediction_commitment", "candidate_changed",
        "evaluator_changed", "threshold_changed", "feature_contract_changed",
        "event_contract_changed", "state_policy_changed", "detected_data_overlap",
        "dataset_manifest_changed", "label_commitment_mismatch",
        "prediction_commitment_mismatch", "missing_provenance",
        "unsupported_data_format", "privacy_finding", "exposed_credentials",
        "prohibited_payload", "external_route_detected", "backend_call_detected",
        "automatic_action_detected", "corrupted_bundle", "role_conflict",
        "chronology_violation", "insufficient_sample_plan",
        "unverifiable_data_origin", "evaluator_nondeterminism",
        "incomplete_prediction_set", "post_hoc_exclusions",
        "unauthorized_retry_after_label_reveal",
    ]
    return {
        "schema_version": "v0318_stop_conditions_v1",
        "stage": "v0.3.18", "status": "frozen",
        "conditions": conditions,
        "outcomes": [
            "trial_stopped", "trial_invalidated", "trial_failed_scientifically",
            "trial_failed_operationally", "trial_completed_passed",
            "trial_completed_failed",
        ],
        "negative_result_must_be_preserved": True,
        "replacement_attempt_requires_new_revision": True,
    }


def main() -> int:
    values = {
        "role_separation_matrix.json": role_matrix(),
        "data_acceptance_policy.json": data_acceptance(),
        "contamination_policy.json": contamination(),
        "blind_holdout_protocol.json": blind_protocol(),
        "metric_policy.json": metric_policy(),
        "sample_sufficiency_policy.json": sufficiency_policy(),
        "stop_conditions.json": stop_conditions(),
    }
    for name, value in values.items():
        write(name, value)
    print(json.dumps({"frozen_design_report_count": len(values)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
