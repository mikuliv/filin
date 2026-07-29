from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "lab_console" / "contracts" / "v0_4_7_1"
NAMES = [
    "failed_criterion_descriptor_v1", "failed_criterion_catalog_v1",
    "critical_difference_descriptor_v1", "critical_difference_catalog_v1",
    "blind_validation_error_case_v1", "blind_validation_error_group_v1",
    "blind_validation_error_atlas_v1", "feature_availability_assessment_v1",
    "feature_shift_assessment_v1", "class_failure_assessment_v1",
    "scenario_failure_assessment_v1", "threshold_diagnostic_assessment_v1",
    "preprocessing_diagnostic_assessment_v1", "root_cause_hypothesis_v1",
    "root_cause_assessment_v1", "corrective_action_v1",
    "corrective_action_catalog_v1", "post_blind_knowledge_transfer_v1",
    "prohibited_data_reuse_v1", "laboratory_autonomy_policy_v1",
    "corrective_proposal_design_v1", "corrective_proposal_readiness_gate_v1",
    "v0_4_7_1_review_v1", "v0_4_7_1_policy_result_v1",
]


def schema(name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"filin://v0.4.7.1/{name}",
        "title": name,
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "payload"],
        "properties": {
            "schema_version": {"const": name},
            "payload": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_.:-]{1,127}$"},
                    "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                    "relative_locator": {"type": "string", "pattern": "^(?![A-Za-z]:|/|.*\\.\\.).{1,240}$"},
                    "status": {"type": "string", "enum": ["passed", "failed", "ready", "conditionally_ready", "not_ready", "confirmed", "strongly_supported", "partially_supported", "hypothesis_only", "unknown"]},
                    "frozen": {"type": "boolean"},
                    "items": {"type": "array", "uniqueItems": True, "maxItems": 10000},
                    "note_ru": {"type": "string", "minLength": 1, "maxLength": 4000, "pattern": "^[^<>]*$"},
                },
            },
        },
    }


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        path = TARGET / f"{name}.schema.json"
        path.write_text(json.dumps(schema(name), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"contract_count": len(NAMES), "target": TARGET.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
