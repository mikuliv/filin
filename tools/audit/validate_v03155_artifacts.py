from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_15_5"


def validate() -> dict:
    errors = []
    policy = json.loads((REPORT / "v0_3_15_5_policy_result.json").read_text(encoding="utf-8"))
    if policy["stage_status"] != "completed" or not policy["v03155_independent_holdout_valid"]: errors.append("stage_not_completed_valid")
    if policy["v03155_independent_holdout_passed"] or policy["candidate_v03154_promoted"]: errors.append("failed_runtime_must_block_promotion")
    if not policy["candidate_window_policy_passed"] or not policy["candidate_conformal_policy_passed"]: errors.append("scientific_result_missing")
    if policy["integrated_runtime_passed"] or policy["source_sink_reconciliation_passed"]: errors.append("runtime_defect_hidden")
    if any(policy[key] for key in ["candidate_ready_for_shadow_mode", "sensor_ready_for_backend_integration", "backend_integration_allowed", "shadow_mode_allowed", "production_ready", "automatic_enforcement_ready", "external_validation_completed"]): errors.append("readiness_prohibition_broken")
    baseline = json.loads((REPORT / "baseline_metrics.json").read_text(encoding="utf-8"))
    if baseline["status"] != "not_applicable_baseline_ineligible" or baseline["passed"] is not None: errors.append("baseline_na_invalid")
    return {"schema_version": "v03155_artifact_validation_v1", "artifact_exclusion_validator_passed": not errors,
            "error_count": len(errors), "errors": errors}


if __name__ == "__main__":
    value = validate(); print(json.dumps(value, ensure_ascii=False, sort_keys=True)); raise SystemExit(0 if value["artifact_exclusion_validator_passed"] else 1)
