from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "lab_console" / "contracts" / "v0_4_7_2"
NAMES = [
    "corrective_data_descriptor_v1", "corrective_development_data_catalog_v1", "corrective_data_generation_plan_v1",
    "corrective_data_isolation_check_v1", "corrective_data_isolation_gate_v1", "corrective_candidate_split_v1",
    "corrective_split_overlap_assessment_v1", "corrective_training_recipe_v1", "corrective_training_recipe_catalog_v1",
    "corrective_training_run_plan_v1", "corrective_training_identity_v1", "corrective_training_status_v1",
    "corrective_training_record_v1", "corrective_training_environment_v1", "corrective_model_artifact_v1",
    "corrective_model_semantic_fingerprint_v1", "corrective_training_reproducibility_v1", "corrective_candidate_proposal_v1",
    "corrective_candidate_proposal_manifest_v1", "corrective_proposal_lineage_v1", "corrective_internal_screening_pack_v1",
    "corrective_internal_screening_plan_v1", "corrective_internal_screening_result_v1", "corrective_admission_criterion_v1",
    "corrective_admission_gate_v1", "corrective_active_comparison_v1", "corrective_previous_proposal_comparison_v1",
    "corrected_failure_assessment_v1", "corrective_regression_assessment_v1", "corrective_proposal_review_v1",
    "corrective_proposal_decision_v1", "corrective_proposal_export_v1", "prohibited_blind_pack_reuse_assessment_v1",
    "post_failure_knowledge_declaration_v1", "v0_4_7_2_console_state_v1", "v0_4_7_2_policy_result_v1",
]


def schema(name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"filin://v0.4.7.2/{name}",
        "title": name, "type": "object", "additionalProperties": False, "required": ["schema_version", "payload"],
        "properties": {
            "schema_version": {"const": name},
            "payload": {"type": "object", "additionalProperties": False, "properties": {
                "id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_.:-]{1,127}$"},
                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "relative_locator": {"type": "string", "pattern": "^(?![A-Za-z]:|/|.*\\.\\.).{1,240}$"},
                "status": {"type": "string", "minLength": 2, "maxLength": 80}, "frozen": {"type": "boolean"},
                "laboratory_only": {"type": "boolean"}, "items": {"type": "array", "uniqueItems": True, "maxItems": 20000},
                "note_ru": {"type": "string", "minLength": 1, "maxLength": 4000, "pattern": "^[^<>]*$"},
            }},
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
