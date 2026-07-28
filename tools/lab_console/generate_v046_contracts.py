from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "lab_console" / "contracts" / "v0_4_6"
NAMES = [
    "candidate_development_data_descriptor_v1", "candidate_development_data_catalog_v1", "candidate_development_split_v1", "split_overlap_assessment_v1",
    "leakage_check_result_v1", "leakage_assessment_v1", "training_recipe_descriptor_v1", "training_recipe_catalog_v1", "training_recipe_binding_v1",
    "training_run_plan_v1", "training_run_identity_v1", "training_run_status_v1", "training_run_record_v1", "training_environment_snapshot_v1",
    "training_dependency_snapshot_v1", "model_artifact_descriptor_v1", "model_semantic_fingerprint_v1", "model_artifact_integrity_v1",
    "training_reproducibility_assessment_v1", "candidate_proposal_v1", "candidate_proposal_manifest_v1", "candidate_proposal_lineage_v1",
    "proposal_evaluation_binding_v1", "proposal_compatibility_assessment_v1", "internal_screening_plan_v1", "internal_screening_result_v1",
    "admission_criterion_v1", "admission_gate_definition_v1", "admission_gate_result_v1", "proposal_active_candidate_comparison_v1",
    "candidate_proposal_review_session_v1", "candidate_proposal_review_step_v1", "candidate_proposal_review_decision_v1", "candidate_proposal_export_v1",
    "v0_4_6_console_state_v1", "model_license_status_v1", "screening_unlock_record_v1", "proposal_invalidation_record_v1",
    "proposal_lineage_successor_v1", "v0_4_6_policy_result_v1",
]
SHA = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
TOKEN = {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{1,79}$", "minLength": 2, "maxLength": 80}
SAFE_TEXT = {"type": "string", "minLength": 1, "maxLength": 4000, "pattern": "^[^<>\\r\\n]*$"}


def schema(name: str) -> dict:
    properties = {
        "schema_version": {"const": name}, "id": TOKEN, "token": TOKEN, "status": {"type": "string", "minLength": 2, "maxLength": 80, "pattern": "^[a-z][a-z0-9_]*$"},
        "sha256": SHA, "proposal_id": {"type": "string", "pattern": "^proposal:v046:[a-f0-9]{8,32}$"}, "candidate_id": {"type": ["null"]},
        "runtime_token": TOKEN, "items": {"type": "array", "maxItems": 10000, "uniqueItems": True, "items": {"type": ["string", "number", "integer", "boolean", "object", "array", "null"]}},
        "flags": {"type": "object", "additionalProperties": {"type": "boolean"}}, "metadata": {"type": "object", "maxProperties": 200},
        "note": SAFE_TEXT, "laboratory_only": {"const": True}, "distribution_allowed": {"const": False}, "no_candidate_registration": {"const": True},
        "no_active_candidate_change": {"const": True}, "absolute_path": {"type": "null"},
    }
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": name, "title": name, "type": "object", "additionalProperties": False,
            "required": ["schema_version"], "properties": properties, "allOf": [{"not": {"required": ["absolute_path"], "properties": {"absolute_path": {"type": "string"}}}}]}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        (OUT / f"{name}.schema.json").write_text(json.dumps(schema(name), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"contract_count": len(NAMES), "output": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__": raise SystemExit(main())
