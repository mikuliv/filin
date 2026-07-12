"""Единый guarded runner research-этапа v0.3.4.

Без путей model/report/artifact он намеренно выполняет только безопасный
preflight: это позволяет проверить конфигурацию без запуска Docker-кампании.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"ml"/"training"),str(ROOT/"lab"/"campaigns"),str(ROOT/"lab"/"training")]
from v034_campaign import load_campaign
from v034_data_access import assert_allowed_campaign,load_policy,policy_sha256
from v0_3_4_preflight import preflight

def atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); temporary=path.with_suffix(path.suffix+".tmp");temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8");temporary.replace(path)

def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("--training-campaign",required=True);parser.add_argument("--validation-campaign",required=True);parser.add_argument("--data-access-policy",required=True);parser.add_argument("--model-selection-policy");parser.add_argument("--output-root",default="lab/output");parser.add_argument("--report-dir");parser.add_argument("--artifact-dir");parser.add_argument("--strict",action="store_true");parser.add_argument("--resume",action="store_true");args=parser.parse_args()
    policy_path=Path(args.data_access_policy); policy=load_policy(policy_path); train=load_campaign(Path(args.training_campaign)); valid=load_campaign(Path(args.validation_campaign));assert_allowed_campaign(train["campaign_id"],"training",policy);assert_allowed_campaign(valid["campaign_id"],"validation",policy)
    checks={**preflight(Path(args.training_campaign)),**preflight(Path(args.validation_campaign))}
    base={"v034_data_access_valid":True,"data_access_policy_sha256":policy_sha256(policy_path),"training_runs_planned":len(train["runs"]),"validation_runs_planned":len(valid["runs"]),"v033_feature_rows_loaded":False,"preflight":checks}
    # Existing callers can verify isolation without authorising expensive execution.
    if not (args.model_selection_policy and args.report_dir and args.artifact_dir):
        print(json.dumps({**base,"status":"preflight_only_no_campaign_execution"},ensure_ascii=False,indent=2)); return
    output=Path(args.output_root); reports=Path(args.report_dir); artifacts=Path(args.artifact_dir)
    for campaign in (args.training_campaign,args.validation_campaign):
        command=[sys.executable,str(ROOT/"lab"/"campaigns"/"run_v034_campaign.py"),"--campaign",campaign,"--output-root",str(output),"--strict"]
        if args.resume: command.append("--resume")
        subprocess.run(command,cwd=ROOT,check=True)
    train_files=sorted((output/"datasets").glob("windows_network_sensor_v0_4_run_v034_train_*.csv")); validation_files=sorted((output/"datasets").glob("windows_network_sensor_v0_4_run_v034_validation_*.csv"))
    if len(train_files)!=12 or len(validation_files)!=6: raise RuntimeError("Кампании v0.3.4 не сформировали ожидаемые 12/6 datasets")
    selection=reports/"cross_validation_results.json"
    command=[sys.executable,str(ROOT/"ml"/"training"/"run_v0_3_4_model_selection.py"),"--datasets",*[str(p) for p in train_files],"--policy",args.model_selection_policy,"--data-access-policy",args.data_access_policy,"--output",str(selection)]
    subprocess.run(command,cwd=ROOT,check=True)
    from v034_candidate_freeze import freeze
    freeze_result=freeze(selection,train_files,policy_path,Path(args.model_selection_policy),Path(args.training_campaign),artifacts,ROOT/"ml"/"experiments"/"v0_3_4"/"frozen_candidate_manifest.yaml")
    atomic(reports/"candidate_freeze_audit.json",freeze_result)
    result={**base,"v034_training_campaign_completed":True,"v034_validation_campaign_completed":True,"v034_cv_completed":True,"v034_cv_passed":bool(freeze_result.get("candidate_frozen")),"candidate_frozen":bool(freeze_result.get("candidate_frozen")),"model_trained_on_v033_data":False,"sensor_ready_for_backend_integration":False}
    if freeze_result.get("candidate_frozen"):
        validation_output=reports/"internal_validation_metrics.json"
        subprocess.run([sys.executable,str(ROOT/"ml"/"experiments"/"v0_3_4"/"run_internal_validation.py"),"--manifest",str(ROOT/"ml"/"experiments"/"v0_3_4"/"frozen_candidate_manifest.yaml"),"--artifact",freeze_result["artifact"],"--datasets",*[str(p) for p in validation_files],"--data-access-policy",args.data_access_policy,"--policy",args.model_selection_policy,"--output",str(validation_output)],cwd=ROOT,check=True)
        validation=json.loads(validation_output.read_text(encoding="utf-8"));result.update(validation)
    else: result.update({"v034_internal_validation_completed":False,"v034_internal_validation_passed":False,"candidate_ready_for_v035":False})
    atomic(reports/"v0_3_4_policy_result.json",result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
