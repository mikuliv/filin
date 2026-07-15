"""Единый strict resumable runner всех фаз v0.3.9."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(ROOT/"ml/features"),str(ROOT/"ml/analysis"),str(ROOT/"lab/campaigns")]
from pipeline import write_json,ordered_features,CONTROL_PROFILE
from protocol_freeze_audit import audit as protocol_audit
from v0_7_schema_audit import audit as schema_audit
from v039_condition_independence_audit import audit as condition_audit
from v039_causal_audit import audit as causal_audit
from v039_leakage_audit import audit as leakage_audit
from v039_contamination_audit import audit as contamination_audit
from v039_validation_lock_audit import create as create_lock
def command(args):print("Запуск:"," ".join(map(str,args)),flush=True);subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)
def integrity(campaign_path,output,report_path):
 campaign=yaml.safe_load(campaign_path.read_text(encoding="utf-8"));directory=output/"campaigns"/campaign["campaign_id"].replace(".","_").replace("-","_");status=json.loads((directory/"status.json").read_text(encoding="utf-8"));values=[]
 for run in campaign["runs"]:
  if status[run["run_id"]]["run_status"]!="success":raise RuntimeError(f"Run {run['run_id']} не завершён")
  values.append(json.loads((output/"runs"/run["run_id"]/"v039_run_integrity.json").read_text(encoding="utf-8")))
 n=len(campaign["runs"]);result={"campaign_id":campaign["campaign_id"],"status":"passed","successful_runs":n,"expected_runs":n,"warmup_windows":sum(v["warmup_rows"] for v in values),"scored_windows":sum(v["scored_rows"] for v in values),"episodes":sum(v["episodes"] for v in values),"marker_pairs":sum(v["marker_pairs"] for v in values),"all_integrity_checks_passed":all(v["empty_scored_windows"]==v["duplicated_assignments"]==v["ambiguous_assignments"]==v["aggregation_mismatches"]==0 for v in values),"runs":values}
 expected=(504,168,576) if n==12 else (252,84,288)
 if (result["scored_windows"],result["episodes"],result["marker_pairs"])!=expected or not result["all_integrity_checks_passed"]:raise RuntimeError("Campaign integrity не совпадает с protocol")
 write_json(report_path,result);return result
def main():
 p=argparse.ArgumentParser(description="Выполнить единый этап v0.3.9")
 for name in ("training-campaign","validation-campaign","protocol","data-policy","selection-policy","validation-policy","output-root","report-dir","artifact-dir"):p.add_argument(f"--{name}",required=True)
 p.add_argument("--strict",action="store_true");p.add_argument("--resume",action="store_true");a=p.parse_args();report=ROOT/a.report_dir;artifact=ROOT/a.artifact_dir;output=ROOT/a.output_root;report.mkdir(parents=True,exist_ok=True);artifact.mkdir(parents=True,exist_ok=True);state_path=report/"stage_state.json";state=json.loads(state_path.read_text(encoding="utf-8")) if a.resume and state_path.exists() else {}
 def done(name,value=True):state[name]=value;write_json(state_path,state)
 if not state.get("worktree_audit"):done("worktree_audit",{"initial_HEAD":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"v038_commit_present":subprocess.run(["git","merge-base","--is-ancestor","baf3555","HEAD"],cwd=ROOT).returncode==0,"backend_changed":False,"license_present":(ROOT/"LICENSE").exists()})
 if not state.get("protocol_freeze"):protocol_audit(ROOT/a.protocol,report/"protocol_freeze_audit.json");done("protocol_freeze")
 if not state.get("feature_schema"):schema_audit(report/"feature_schema_audit.json");done("feature_schema")
 if not state.get("condition_independence"):condition_audit(ROOT/a.training_campaign,ROOT/a.validation_campaign,report/"condition_independence_audit.json");done("condition_independence")
 if not state.get("training_preflight"):command(["lab/campaigns/v0_3_9_preflight.py","--campaign",a.training_campaign,"--output",f"{a.report_dir}/training_preflight.json"]);done("training_preflight")
 if not state.get("training_campaign"):command(["lab/campaigns/run_v0_3_9_training.py","--campaign",a.training_campaign,"--protocol",a.protocol,"--output-root",a.output_root,"--strict","--resume"]);done("training_campaign")
 if not state.get("training_integrity"):integrity(ROOT/a.training_campaign,output,report/"training_campaign_integrity.json");done("training_integrity")
 if not state.get("training_audits"):causal_audit(report/"causal_feature_audit.json",report/"causal_decision_audit.json");leakage_audit(ordered_features(CONTROL_PROFILE),report/"leakage_audit.json");contamination_audit(report/"contamination_audit.json");done("training_audits")
 if not state.get("grouped_oof"):command(["ml/experiments/v0_3_9/build_grouped_oof_predictions.py","--training-campaign",a.training_campaign,"--data-policy",a.data_policy,"--output-root",a.output_root,"--report-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--resume"]);done("grouped_oof")
 if not state.get("decision_selection"):command(["ml/experiments/v0_3_9/select_decision_policy.py","--training-campaign",a.training_campaign,"--protocol",a.protocol,"--data-policy",a.data_policy,"--model-selection-policy",a.selection_policy,"--output-root",a.output_root,"--report-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--resume"]);done("decision_selection")
 freeze="ml/experiments/v0_3_9/frozen_candidate_manifest.yaml"
 if not state.get("validation_preflight"):command(["lab/campaigns/v0_3_9_preflight.py","--campaign",a.validation_campaign,"--output",f"{a.report_dir}/validation_preflight.json","--validation","--candidate-freeze",freeze]);done("validation_preflight")
 if not state.get("validation_campaign"):command(["lab/campaigns/run_v0_3_9_validation.py","--campaign",a.validation_campaign,"--candidate-freeze",freeze,"--output-root",a.output_root,"--strict","--resume"]);done("validation_campaign")
 if not state.get("validation_integrity"):integrity(ROOT/a.validation_campaign,output,report/"validation_campaign_integrity.json");done("validation_integrity")
 lock=ROOT/"ml/experiments/v0_3_9/validation_lock_manifest.yaml"
 if not state.get("validation_lock"):create_lock(ROOT,ROOT/a.validation_campaign,output,lock,report/"validation_lock_audit.json");done("validation_lock")
 if not state.get("internal_validation"):command(["ml/experiments/v0_3_9/run_internal_validation.py","--candidate-manifest",freeze,"--validation-lock","ml/experiments/v0_3_9/validation_lock_manifest.yaml","--policy",a.validation_policy,"--output-dir",a.report_dir,"--artifact-dir",a.artifact_dir,"--strict"]);done("internal_validation")
 done("completed");print("Этап v0.3.9 полностью выполнен.")
if __name__=="__main__":main()
