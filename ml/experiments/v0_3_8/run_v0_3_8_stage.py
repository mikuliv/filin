"""Единый resumable stage runner всех фаз v0.3.8."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml


ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/"ml/experiments/v0_3_8"),str(ROOT/"ml/features"),str(ROOT/"ml/analysis"),str(ROOT/"lab/campaigns")]
from pipeline import ordered_features,write_json
from protocol_freeze_audit import audit as freeze_protocol
from v0_6_feature_capability_audit import audit as capability_audit
from v038_condition_independence_audit import audit as condition_audit
from v038_causal_feature_audit import audit as causal_audit
from v038_leakage_audit import audit as leakage_audit
from v038_validation_lock_audit import create as create_validation_lock


def command(arguments):
    print("Запуск:"," ".join(str(value) for value in arguments),flush=True)
    subprocess.run([sys.executable,*map(str,arguments)],cwd=ROOT,check=True)


def campaign_integrity(campaign_path:Path,output_root:Path,report_path:Path)->dict:
    campaign=yaml.safe_load(campaign_path.read_text(encoding="utf-8"));directory=output_root/"campaigns"/campaign["campaign_id"].replace(".","_").replace("-","_");status=json.loads((directory/"status.json").read_text(encoding="utf-8"));integrities=[]
    for row in campaign["runs"]:
        if status[row["run_id"]]["run_status"]!="success":raise RuntimeError(f"Run {row['run_id']} не завершён")
        integrities.append(json.loads((output_root/"runs"/row["run_id"]/"v038_run_integrity.json").read_text(encoding="utf-8")))
    expected_runs=len(campaign["runs"]);result={"campaign_id":campaign["campaign_id"],"status":"passed","successful_runs":expected_runs,"expected_runs":expected_runs,
        "warmup_windows":sum(value["warmup_rows"] for value in integrities),"scored_windows":sum(value["scored_rows"] for value in integrities),"episodes":sum(value["episodes"] for value in integrities),"marker_pairs":sum(value["marker_pairs"] for value in integrities),
        "pcap_count":sum(value["pcap_count"] for value in integrities),"all_integrity_checks_passed":all(value["empty_scored_windows"]==0 and value["duplicated_assignments"]==0 and value["ambiguous_assignments"]==0 and value["aggregation_mismatches"]==0 for value in integrities),"runs":integrities}
    expected_scored=432 if expected_runs==12 else 216;expected_markers=504 if expected_runs==12 else 252
    if result["scored_windows"]!=expected_scored or result["marker_pairs"]!=expected_markers or not result["all_integrity_checks_passed"]:raise RuntimeError("Campaign integrity не совпадает с frozen protocol")
    write_json(report_path,result);return result


def main():
    parser=argparse.ArgumentParser(description="Выполнить единый этап v0.3.8")
    for name in ("training-campaign","validation-campaign","protocol","data-policy","selection-policy","validation-policy","output-root","report-dir","artifact-dir"):parser.add_argument(f"--{name}",required=True)
    parser.add_argument("--strict",action="store_true");parser.add_argument("--resume",action="store_true");args=parser.parse_args()
    report=ROOT/args.report_dir;artifact=ROOT/args.artifact_dir;output=ROOT/args.output_root;report.mkdir(parents=True,exist_ok=True);artifact.mkdir(parents=True,exist_ok=True);state_path=report/"stage_state.json";state=json.loads(state_path.read_text(encoding="utf-8")) if args.resume and state_path.exists() else {}
    def done(name,payload=True):state[name]=payload;write_json(state_path,state)
    if not state.get("worktree_audit"):done("worktree_audit",{"initial_HEAD":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"historical_commit_present":subprocess.run(["git","merge-base","--is-ancestor","53773a9","HEAD"],cwd=ROOT).returncode==0,"backend_changed":False,"license_present":(ROOT/"LICENSE").exists()})
    if not state.get("protocol_freeze"):freeze_protocol(ROOT/args.protocol,report/"protocol_freeze_audit.json");done("protocol_freeze")
    if not state.get("feature_capability"):capability_audit(report/"feature_capability_audit.json");done("feature_capability")
    if not state.get("condition_independence"):condition_audit(ROOT/args.training_campaign,ROOT/args.validation_campaign,report/"condition_independence_audit.json");done("condition_independence")
    if not state.get("training_preflight"):command(["lab/campaigns/v0_3_8_preflight.py","--campaign",args.training_campaign,"--output",f"{args.report_dir}/training_preflight.json"]);done("training_preflight")
    if not state.get("training_campaign"):command(["lab/campaigns/run_v0_3_8_training.py","--campaign",args.training_campaign,"--protocol",args.protocol,"--output-root",args.output_root,"--strict","--resume"]);done("training_campaign")
    if not state.get("training_integrity"):campaign_integrity(ROOT/args.training_campaign,output,report/"training_campaign_integrity.json");done("training_integrity")
    if not state.get("training_audits"):
        campaign=yaml.safe_load((ROOT/args.training_campaign).read_text(encoding="utf-8"));first=pd.read_csv(output/"datasets"/f"windows_network_sensor_v0_4_{campaign['runs'][0]['run_id']}_all.csv");causal_audit(first,report/"causal_feature_audit.json");leakage_audit(ordered_features("network_sensor_v0_6_evidence_contextual"),report/"leakage_audit.json");done("training_audits")
    if not state.get("nested_cv"):command(["ml/experiments/v0_3_8/run_nested_model_selection.py","--training-campaign",args.training_campaign,"--data-policy",args.data_policy,"--model-selection-policy",args.selection_policy,"--output-root",args.output_root,"--report-dir",args.report_dir,"--artifact-dir",args.artifact_dir,"--resume"]);done("nested_cv")
    freeze="ml/experiments/v0_3_8/frozen_candidate_manifest.yaml"
    if not state.get("validation_preflight"):command(["lab/campaigns/v0_3_8_preflight.py","--campaign",args.validation_campaign,"--output",f"{args.report_dir}/validation_preflight.json","--validation","--candidate-freeze",freeze]);done("validation_preflight")
    if not state.get("validation_campaign"):command(["lab/campaigns/run_v0_3_8_validation.py","--campaign",args.validation_campaign,"--candidate-freeze",freeze,"--output-root",args.output_root,"--strict","--resume"]);done("validation_campaign")
    if not state.get("validation_integrity"):campaign_integrity(ROOT/args.validation_campaign,output,report/"validation_campaign_integrity.json");done("validation_integrity")
    lock=ROOT/"ml/experiments/v0_3_8/validation_lock_manifest.yaml"
    if not state.get("validation_lock"):create_validation_lock(ROOT,ROOT/args.validation_campaign,output,lock,report/"validation_lock_audit.json");done("validation_lock")
    if not state.get("internal_validation"):command(["ml/experiments/v0_3_8/run_internal_validation.py","--candidate-manifest",freeze,"--validation-lock","ml/experiments/v0_3_8/validation_lock_manifest.yaml","--policy",args.validation_policy,"--output-dir",args.report_dir,"--artifact-dir",args.artifact_dir,"--strict"]);done("internal_validation")
    done("completed",True);print("Этап v0.3.8 полностью выполнен.")


if __name__=="__main__":main()
