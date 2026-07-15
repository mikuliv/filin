"""Единый resumable stage runner полного цикла v0.3.10."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/"lab/campaigns"),str(ROOT/"ml/analysis"),str(ROOT/"ml/features"),str(HERE)]

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
    from network_sensor_v0_6 import CONTROL_PROFILE,ordered_features
    schema_audit(report/"feature_schema_audit.json")
    causal_audit(report/"causal_feature_audit.json",report/"causal_decision_audit.json")
    leakage_audit(ordered_features(CONTROL_PROFILE),report/"leakage_audit.json")
    state["audits"]="completed";save(state_path,state)
    if not (report/"training_preflight.json").exists():command(["lab/campaigns/v0_3_10_preflight.py","--campaign",a.training_campaign,"--output",str((report/"training_preflight.json").relative_to(ROOT))])
    command(["lab/campaigns/run_v0_3_10_training.py","--campaign",a.training_campaign,"--protocol",a.protocol,"--output-root",a.output_root,"--strict","--resume"])
    state["training"]="completed";save(state_path,state)
    command(["ml/experiments/v0_3_10/build_grouped_oof_predictions.py","--training-campaign",a.training_campaign,"--data-policy",a.data_policy,"--output-root",a.output_root,"--report-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--resume"])
    command(["ml/experiments/v0_3_10/run_nested_decision_selection.py","--training-campaign",a.training_campaign,"--protocol",a.protocol,"--data-policy",a.data_policy,"--model-selection-policy",a.selection_policy,"--output-root",a.output_root,"--report-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--resume"])
    state["candidate_freeze"]="completed";save(state_path,state)
    freeze_manifest="ml/experiments/v0_3_10/frozen_candidate_manifest.yaml"
    if not (report/"validation_preflight.json").exists():command(["lab/campaigns/v0_3_10_preflight.py","--campaign",a.validation_campaign,"--output",str((report/"validation_preflight.json").relative_to(ROOT)),"--validation","--candidate-freeze",freeze_manifest])
    command(["lab/campaigns/run_v0_3_10_validation.py","--campaign",a.validation_campaign,"--candidate-freeze",freeze_manifest,"--output-root",a.output_root,"--strict","--resume"])
    state["validation"]="completed";save(state_path,state)
    lock=HERE/"validation_lock_manifest.yaml"
    from v0310_validation_lock_audit import create,verify
    if not lock.exists():create(ROOT,ROOT/a.validation_campaign,ROOT/a.output_root,lock,report/"validation_lock_audit.json")
    if not verify(ROOT,lock)["validation_lock_valid"]:raise RuntimeError("Validation lock не прошёл повторную проверку")
    state["validation_lock"]="completed";save(state_path,state)
    command(["ml/experiments/v0_3_10/run_internal_validation.py","--candidate-manifest",freeze_manifest,"--validation-lock",str(lock.relative_to(ROOT)),"--policy",a.validation_policy,"--output-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--strict","--resume"])
    command(["tools/docs/validate_v0310_summary.py","--summary",str((report/"v0_3_10_summary.md").relative_to(ROOT)),"--strict"])
    state.update({"frozen_evaluation":"completed","summary":"completed","stage":"completed"});save(state_path,state)
    print("Этап v0.3.10 завершён; повторяемые фазы не выполнялись.")

if __name__=="__main__":main()
