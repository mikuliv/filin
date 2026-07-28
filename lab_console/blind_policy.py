from __future__ import annotations

from typing import Any


VIOLATION_CODES = {
    "labels_visible_pre_unlock": "pre_unlock_label_access_forbidden",
    "oracle_visible": "oracle_access_forbidden",
    "role_token_missing": "blind_role_authorization_denied",
    "role_token_reused": "role_capability_reuse_forbidden",
    "role_overlap": "role_workspace_overlap",
    "protocol_mutated": "frozen_protocol_immutable",
    "control_pack_mutated": "control_pack_immutable",
    "label_package_mutated": "label_package_immutable",
    "prediction_plan_mutated": "prediction_plan_immutable",
    "prediction_package_mutated": "prediction_package_immutable",
    "overlap_detected": "data_overlap_detected",
    "overlap_not_checked": "overlap_gate_required",
    "blindness_failed": "blindness_gate_required",
    "inference_before_plan": "prediction_plan_not_frozen",
    "unlock_before_commitments": "prediction_commitments_required",
    "unlock_without_authorization": "label_unlock_authorization_required",
    "post_unlock_inference": "official_inference_after_label_unlock_forbidden",
    "missing_prediction": "missing_prediction_rejected",
    "duplicate_prediction": "duplicate_prediction_rejected",
    "invalid_prediction": "invalid_prediction_rejected",
    "changed_population": "comparison_population_mismatch",
    "changed_metric_contract": "metric_contract_mismatch",
    "changed_class_contract": "class_contract_mismatch",
    "hidden_weight": "hidden_weight_forbidden",
    "winner_score": "winner_selection_forbidden",
    "automatic_promotion": "promotion_forbidden",
    "candidate_registration": "candidate_registration_forbidden",
    "active_candidate_change": "active_candidate_change_forbidden",
    "threshold_change": "threshold_change_forbidden",
    "retrain": "retraining_forbidden",
    "model_upload": "model_upload_forbidden",
    "dataset_upload": "dataset_upload_forbidden",
    "network_access": "network_forbidden",
    "shell_command": "arbitrary_command_forbidden",
    "absolute_path": "absolute_path_forbidden",
    "path_traversal": "invalid_runtime_token",
    "secret_export": "secret_in_export",
    "binary_export": "model_binary_export_forbidden",
    "dataset_export": "dataset_export_forbidden",
    "labels_export": "label_export_forbidden",
    "sqlite_export": "sqlite_export_forbidden",
    "independent_human_claim": "independent_human_claim_forbidden",
    "passed_failed_gate": "mandatory_gate_failed",
    "v048_after_failure": "next_stage_forbidden",
    "protected_material_mutation": "protected_file_immutable",
    "backend_mutation": "backend_tree_immutable",
    "git_history_operation": "git_operation_forbidden",
}


def validate_policy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a temporary adversarial payload without executing its requested action."""
    violation = payload.get("violation")
    if violation in VIOLATION_CODES:
        return {"accepted": False, "error_code": VIOLATION_CODES[violation], "executed": True}
    required = {"protocol_frozen", "labels_locked", "prediction_plan_frozen", "network_disabled"}
    if not required.issubset(payload) or not all(payload[key] is True for key in required):
        return {"accepted": False, "error_code": "safe_preconditions_required", "executed": True}
    return {"accepted": True, "error_code": None, "executed": True}
