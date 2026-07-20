from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
def load(name): return json.loads((ROOT/"ml/reports/v0_3_13"/name).read_text(encoding="utf-8"))

def audit():
    policy=load("v0_3_13_policy_result.json"); resume=load("resume_audit.json"); prediction=load("immutable_prediction_manifest.json"); lock=load("holdout_input_lock.json")
    completion=(ROOT/"ml/reports/v0_3_13/regression_bundle_completion.yaml").is_file(); summary=(ROOT/"ml/reports/v0_3_13/v0_3_13_summary.md").read_text(encoding="utf-8")
    prediction_not_repeated=resume.get("prediction_repeated") is False and resume.get("immutable_prediction_sha256")==__import__("hashlib").sha256((ROOT/"ml/reports/v0_3_13/immutable_prediction_manifest.json").read_bytes()).hexdigest()
    stages_not_repeated=resume.get("completed_stage_skipped") is True
    keys_match=prediction.get("input_lock_sha256")==lock.get("input_lock_sha256") and completion
    strict_ok=resume.get("strict_resume_passed") is True and "Strict resume пройден" in summary
    consistent=all((prediction_not_repeated,stages_not_repeated,keys_match,strict_ok))
    stale=policy.get("checkpoint_resume_passed") is False and consistent
    return {"classification":"policy_flag_stale" if stale else "unknown_inconsistency","frozen_policy_flag":policy.get("checkpoint_resume_passed"),"prediction_skipped_on_resume":policy.get("prediction_skipped_on_resume"),"prediction_generated_once":policy.get("prediction_generated_once"),"prediction_not_repeated":prediction_not_repeated,"completed_scientific_stages_not_repeated":stages_not_repeated,"checkpoint_keys_match":keys_match,"strict_resume_completed_without_integrity_mismatch":strict_ok,"v0313_checkpoint_evidence_consistency_passed":consistent,"primary_evidence":["resume_audit.json","holdout_input_lock.json","immutable_prediction_manifest.json","regression_bundle_completion.yaml","v0_3_13_policy_result.json","v0_3_13_summary.md","research-state.yaml"],"interpretation":"Policy result был заморожен до заключительного strict resume; позднее первичное resume evidence не переписывает frozen policy."}
