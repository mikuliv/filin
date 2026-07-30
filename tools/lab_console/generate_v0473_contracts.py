from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "lab_console" / "contracts" / "v0_4_7_3"
NAMES = (
    "blind_validation_role_v0473_v1", "blind_validation_role_assignment_v0473_v1", "internal_blindness_status_v0473_v1",
    "blind_control_data_descriptor_v0473_v1", "blind_control_data_catalog_v0473_v1", "blind_scenario_novelty_assessment_v1",
    "blind_control_pack_v0473_v1", "blind_input_package_v0473_v1", "blind_label_package_v0473_v1", "label_commitment_v0473_v1",
    "data_isolation_check_v0473_v1", "data_isolation_gate_v0473_v1", "blind_leakage_assessment_v0473_v1", "blindness_gate_v0473_v1",
    "blind_criterion_lineage_entry_v1", "blind_criterion_lineage_map_v1", "blind_prediction_plan_v0473_v1", "blind_prediction_plan_binding_v0473_v1",
    "blind_inference_identity_v0473_v1", "blind_inference_status_v0473_v1", "blind_inference_record_v0473_v1", "blind_inference_recovery_record_v1",
    "blind_prediction_row_v0473_v1", "blind_prediction_package_v0473_v1", "prediction_commitment_v0473_v1", "prediction_freeze_record_v0473_v1",
    "label_unlock_authorization_v0473_v1", "label_unlock_record_v0473_v1", "blind_metric_contract_v0473_v1", "blind_evaluation_request_v0473_v1",
    "blind_evaluation_result_v0473_v1", "blind_class_metric_v0473_v1", "blind_episode_metric_v0473_v1", "blind_abstention_metric_v0473_v1",
    "blind_confusion_matrix_v0473_v1", "blind_comparability_assessment_v0473_v1", "previous_failure_resolution_assessment_v1",
    "blind_validation_difference_v0473_v1", "blind_active_proposal_comparison_v0473_v1", "blind_acceptance_criterion_v0473_v1",
    "blind_acceptance_gate_definition_v0473_v1", "blind_acceptance_gate_result_v0473_v1", "blind_validation_review_session_v0473_v1",
    "blind_validation_review_step_v0473_v1", "blind_validation_review_decision_v0473_v1", "blind_validation_invalidation_record_v0473_v1",
    "blind_validation_export_v0473_v1", "blind_validation_lineage_v0473_v1", "blind_validation_audit_event_v0473_v1",
    "v0_4_7_3_console_state_v1", "v0_4_7_3_policy_result_v1",
)


def schema(name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"filin://contracts/v0_4_7_3/{name}",
        "title": name, "description": "Строгий контракт внутренней слепой лабораторной проверки v0.4.7.3.",
        "type": "object", "additionalProperties": False,
        "required": ["schema_version", "record_id", "status", "sha256", "payload"],
        "properties": {
            "schema_version": {"const": name},
            "record_id": {"type": "string", "pattern": "^[a-z][a-z0-9_-]{2,127}$"},
            "status": {"type": "string", "enum": ["created", "frozen", "locked", "passed", "failed", "not_assessable", "invalidated", "completed", "interrupted", "recovered", "comparable"]},
            "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "opaque_token": {"type": "string", "pattern": "^[a-z][a-z0-9-]{7,127}$"},
            "relative_locator": {"type": "string", "pattern": "^(?![A-Za-z]:)(?!/)(?!.*\\.\\.)(?!.*[<>]).{1,240}$"},
            "payload": {"type": "object", "additionalProperties": False, "properties": {}},
        },
    }


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        (TARGET / f"{name}.schema.json").write_text(json.dumps(schema(name), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"contract_count": len(NAMES), "target": TARGET.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
