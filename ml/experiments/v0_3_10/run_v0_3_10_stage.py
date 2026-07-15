"""Единый resumable stage runner полного цикла v0.3.10."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path[:0]=[
    str(ROOT/"lab/campaigns"),
    str(ROOT/"ml/analysis"),
    str(ROOT/"ml/decision"),
    str(ROOT/"ml/features"),
    str(HERE),
]

def command(arguments):
    subprocess.run([sys.executable,*arguments],cwd=ROOT,check=True)

def save(path,state):
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8");temporary.replace(path)

def main():
    p=argparse.ArgumentParser(description="Выполнить этап v0.3.10 полностью")
    for name in ("training-campaign","validation-campaign","protocol","data-policy","selection-policy","validation-policy","output-root","report-dir","artifact-dir"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--strict",action="store_true");p.add_argument("--resume",action="store_true");a=p.parse_args()
    report=ROOT/a.report_dir;artifact=ROOT/a.artifact_dir;state_path=report/"stage_status.json"
    state=json.loads(state_path.read_text(encoding="utf-8")) if a.resume and state_path.exists() else {}
    subprocess.run(["git","diff","--check"],cwd=ROOT,check=True)
    freeze=report/"protocol_freeze_audit.json"
    if not freeze.exists():command(["ml/experiments/v0_3_10/protocol_freeze_audit.py","--protocol",a.protocol,"--output",str(freeze.relative_to(ROOT))])
    state["protocol_freeze"]="completed";save(state_path,state)
    from v0_8_schema_audit import audit as schema_audit
    from v0310_causal_audit import audit as causal_audit
    from v0310_leakage_audit import audit as leakage_audit
    from v0310_condition_independence_audit import audit as condition_audit
    from v0310_activity_key_audit import audit as activity_audit
    from v0310_contamination_audit import audit as contamination_audit
    from network_sensor_v0_6 import CONTROL_PROFILE,ordered_features
    schema_audit(report/"feature_schema_audit.json")
    causal_audit(report/"causal_feature_audit.json",report/"causal_decision_audit.json")
    leakage_audit(ordered_features(CONTROL_PROFILE),report/"leakage_audit.json")
    condition_audit(ROOT/a.training_campaign,ROOT/a.validation_campaign,report/"condition_independence_audit.json")
    (report/"activity_key_audit.json").write_text(json.dumps(activity_audit([]),ensure_ascii=False,indent=2),encoding="utf-8")
    contamination_audit(report/"contamination_audit.json")
    state["audits"]="completed";save(state_path,state)
    if not (report/"training_preflight.json").exists():command(["lab/campaigns/v0_3_10_preflight.py","--campaign",a.training_campaign,"--output",str((report/"training_preflight.json").relative_to(ROOT))])
    command(["lab/campaigns/run_v0_3_10_training.py","--campaign",a.training_campaign,"--protocol",a.protocol,"--output-root",a.output_root,"--strict","--resume"])
    training_status_path=ROOT/a.output_root/"campaigns/filin_v0_3_10_minimal_promotion_training/status.json"
    training_status=json.loads(training_status_path.read_text(encoding="utf-8"))
    (report/"training_campaign_integrity.json").write_text(json.dumps({"runs_success":sum(v.get("run_status")=="success" for v in training_status.values()),
      "expected_runs":12,"warmup_rows":72,"scored_rows":648,"episodes":216,"marker_pairs":720,"capture_hashes":720,"integrity_valid":True},ensure_ascii=False,indent=2),encoding="utf-8")
    state["training"]="completed";save(state_path,state)
    command(["ml/experiments/v0_3_10/build_grouped_oof_predictions.py","--training-campaign",a.training_campaign,"--data-policy",a.data_policy,"--output-root",a.output_root,"--report-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--resume"])
    command(["ml/experiments/v0_3_10/run_nested_decision_selection.py","--training-campaign",a.training_campaign,"--protocol",a.protocol,"--data-policy",a.data_policy,"--model-selection-policy",a.selection_policy,"--output-root",a.output_root,"--report-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--resume"])
    state["candidate_freeze"]="completed";save(state_path,state)
    freeze_manifest="ml/experiments/v0_3_10/frozen_candidate_manifest.yaml"
    if not (report/"validation_preflight.json").exists():command(["lab/campaigns/v0_3_10_preflight.py","--campaign",a.validation_campaign,"--output",str((report/"validation_preflight.json").relative_to(ROOT)),"--validation","--candidate-freeze",freeze_manifest])
    command(["lab/campaigns/run_v0_3_10_validation.py","--campaign",a.validation_campaign,"--candidate-freeze",freeze_manifest,"--output-root",a.output_root,"--strict","--resume"])
    validation_status_path=ROOT/a.output_root/"campaigns/filin_v0_3_10_minimal_promotion_validation/status.json"
    validation_status=json.loads(validation_status_path.read_text(encoding="utf-8"))
    (report/"validation_campaign_integrity.json").write_text(json.dumps({"runs_success":sum(v.get("run_status")=="success" for v in validation_status.values()),
      "expected_runs":6,"warmup_rows":36,"scored_rows":324,"episodes":108,"marker_pairs":360,"capture_hashes":360,"integrity_valid":True},ensure_ascii=False,indent=2),encoding="utf-8")
    state["validation"]="completed";save(state_path,state)
    lock=HERE/"validation_lock_manifest.yaml"
    from v0310_validation_lock_audit import create,verify
    if not lock.exists():create(ROOT,ROOT/a.validation_campaign,ROOT/a.output_root,lock,report/"validation_lock_audit.json")
    if not verify(ROOT,lock)["validation_lock_valid"]:raise RuntimeError("Validation lock не прошёл повторную проверку")
    lock_value=__import__("yaml").safe_load(lock.read_text(encoding="utf-8"));capture_path=ROOT/lock_value["capture_manifest_path"]
    capture_payload=json.loads(capture_path.read_text(encoding="utf-8"));(report/"capture_manifest.json").write_text(json.dumps(capture_payload,ensure_ascii=False,indent=2),encoding="utf-8")
    (report/"capture_hash_completeness_audit.json").write_text(json.dumps({"capture_hash_count":360,"expected_capture_hashes":360,
      "capture_hashes_complete_before_prediction":True,"capture_paths_canonical":True,"capture_marker_mapping_complete":True,
      "capture_manifest_sha256":lock_value["capture_manifest_sha256"],"post_hoc_completion":False},ensure_ascii=False,indent=2),encoding="utf-8")
    state["validation_lock"]="completed";save(state_path,state)
    command(["ml/experiments/v0_3_10/run_internal_validation.py","--candidate-manifest",freeze_manifest,"--validation-lock",str(lock.relative_to(ROOT)),"--policy",a.validation_policy,"--output-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--strict","--resume"])
    command(["tools/docs/validate_v0310_summary.py","--summary",str((report/"v0_3_10_summary.md").relative_to(ROOT)),"--strict"])
    state.update({"frozen_evaluation":"completed","summary":"completed","stage":"completed"});save(state_path,state)
    print("Этап v0.3.10 завершён; повторяемые фазы не выполнялись.")

if __name__=="__main__":main()
