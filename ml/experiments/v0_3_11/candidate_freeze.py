"""Создание и проверка frozen candidate manifest до validation collection."""
import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
import joblib,yaml

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def freeze(root:Path,artifact:Path,selection:Path,output:Path):
 selected=json.loads(selection.read_text(encoding="utf-8"))["selected"]
 files={"protocol":"ml/experiments/v0_3_11/protocol.yaml","training_campaign":"lab/campaigns/v0_3_11/training.yaml","feature_schema":"ml/experiments/v0_3_11/feature_schema.yaml","policy_grid":"ml/experiments/v0_3_11/policy_grid.yaml","decision_implementation":"ml/experiments/v0_3_11/state_machine.py","selection_implementation":"ml/experiments/v0_3_11/nested_selection.py","prediction_implementation":"ml/experiments/v0_3_11/immutable_prediction.py","evaluation_implementation":"ml/experiments/v0_3_11/evaluate_validation.py","model_selection_report":selection.resolve().relative_to(root.resolve()).as_posix(),"dependency_lock":"ml/requirements.txt"}
 payload={"candidate_id":selected["candidate_id"],"architecture_id":"network_sensor_v0_9_burden_aware_promotion","state_semantics":"burden_aware_v1","model_family":"hgb_gate_hgb_subtype","feature_count":51,"decision_policy":selected["parameters"],"candidate_artifact_path":artifact.resolve().relative_to(root.resolve()).as_posix(),"candidate_artifact_sha256":sha(artifact),"source_hashes":{k:sha(root/v) for k,v in files.items()},"source_paths":files,"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),"freeze_timestamp":datetime.now(UTC).isoformat(),"frozen_before_validation_collection":True,"model_selection_policy_passed":json.loads(selection.read_text(encoding="utf-8"))["model_selection_policy_passed"]}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(yaml.safe_dump(payload,sort_keys=False,allow_unicode=True),encoding="utf-8");return {**payload,"candidate_manifest_sha256":sha(output)}
def verify(root:Path,manifest:Path):
 for directory in (root/"ml/models",root/"ml/features",root/"ml/decision"):
  if str(directory) not in sys.path:sys.path.insert(0,str(directory))
 p=yaml.safe_load(manifest.read_text(encoding="utf-8"));artifact=root/p["candidate_artifact_path"];checks={"artifact":sha(artifact)==p["candidate_artifact_sha256"]};checks.update({k:sha(root/p["source_paths"][k])==v for k,v in p["source_hashes"].items()});bundle=joblib.load(artifact);required={"gate","subtype","gate_calibrator","subtype_calibrator","conformal","feature_order","classes","decision_parameters","state_semantics_version","dedup_policy","reset_policy","candidate_id","training_campaign_sha256","fold_mapping_sha256","model_selection_report_sha256","source_commit","dependency_lock_sha256"};checks["artifact_contract"]=required<=set(bundle) and len(bundle["feature_order"])==51;return {"candidate_integrity_passed":all(checks.values()),"checks":checks,"candidate_manifest_sha256":sha(manifest)}
