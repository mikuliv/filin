from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "lab_console" / "contracts" / "v0_4_7"
NAMES = [
    "blind_validation_role_v1", "blind_validation_role_assignment_v1", "blind_validation_independence_assessment_v1",
    "blind_control_data_descriptor_v1", "blind_control_data_catalog_v1", "blind_control_pack_v1", "blind_input_package_v1",
    "blind_label_package_v1", "label_commitment_v1", "blind_data_overlap_assessment_v1", "blind_leakage_assessment_v1",
    "blindness_gate_result_v1", "blind_prediction_plan_v1", "blind_prediction_plan_binding_v1", "blind_inference_identity_v1",
    "blind_inference_status_v1", "blind_inference_record_v1", "blind_prediction_row_v1", "blind_prediction_package_v1",
    "prediction_commitment_v1", "prediction_freeze_record_v1", "label_unlock_authorization_v1", "label_unlock_record_v1",
    "blind_metric_contract_v1", "blind_evaluation_request_v1", "blind_evaluation_result_v1", "blind_class_metric_v1",
    "blind_episode_metric_v1", "blind_abstention_metric_v1", "blind_confusion_matrix_v1", "blind_comparability_assessment_v1",
    "blind_validation_difference_v1", "blind_active_proposal_comparison_v1", "blind_acceptance_criterion_v1",
    "blind_acceptance_gate_definition_v1", "blind_acceptance_gate_result_v1", "blind_validation_review_session_v1",
    "blind_validation_review_step_v1", "blind_validation_review_decision_v1", "blind_validation_export_v1",
    "blind_validation_invalidation_record_v1", "blind_validation_lineage_v1", "blind_validation_audit_event_v1",
    "v0_4_7_console_state_v1", "v0_4_7_policy_result_v1",
]


def schema(name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"filin://v0.4.7/{name}",
        "title": name, "type": "object", "additionalProperties": False, "required": ["schema_version", "payload"],
        "properties": {
            "schema_version": {"type": "string", "const": name},
            "payload": {"type": "object", "additionalProperties": False, "properties": {
                "opaque_token": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{1,79}$"},
                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "status": {"type": "string", "minLength": 2, "maxLength": 80},
                "frozen": {"type": "boolean"}, "items": {"type": "array", "uniqueItems": True, "maxItems": 10000},
                "relative_locator": {"type": "string", "pattern": "^(?![A-Za-z]:|/|.*\\.\\.).{1,240}$"},
                "note": {"type": "string", "minLength": 1, "maxLength": 4000, "pattern": "^[^<>]*$"},
            }},
        },
    }


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        (TARGET / f"{name}.schema.json").write_text(json.dumps(schema(name), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"contract_count": len(NAMES), "target": str(TARGET)}, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
