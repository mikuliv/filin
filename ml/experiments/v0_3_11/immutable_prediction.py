"""Единственная immutable validation prediction с hash-aware resume."""
import hashlib,json,sys
from pathlib import Path
import joblib,numpy as np,yaml
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/"ml/models")]
from ml.experiments.v0_3_10.pipeline import ATTACK_CLASSES,CLASSES,aligned_probabilities,calibrated_joint
from ml.experiments.v0_3_11.nested_selection import source_rows,decisions
from ml.experiments.v0_3_11.candidate_freeze import verify as verify_candidate
from ml.experiments.v0_3_11.capture_lock import verify as verify_capture
from ml.experiments.v0_3_11.validation_lock import verify as verify_lock
from ml.experiments.v0_3_11.no_fit_guard import ValidationNoFitGuard
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def create(campaign,output_root,artifact,candidate_manifest,capture_manifest,validation_lock,output,resume=False):
 if resume and output.exists():return {"immutable_prediction_created":True,"prediction_skipped_on_resume":True,"immutable_prediction_sha256":sha(output),"validation_prediction_generation_count":1}
 if not verify_candidate(ROOT,candidate_manifest)["candidate_integrity_passed"] or not verify_capture(ROOT,capture_manifest)["capture_lock_passed"] or not verify_lock(validation_lock)["validation_lock_passed"]:raise RuntimeError("Prediction integrity gate failed")
 rows,X=source_rows(campaign,output_root);bundle=joblib.load(artifact)
 with ValidationNoFitGuard() as guard:
  gate=aligned_probabilities(bundle["gate"],X,["0","1"])[:,1];sub=aligned_probabilities(bundle["subtype"],X,ATTACK_CLASSES);probs=calibrated_joint(bundle["gate_calibrator"],bundle["subtype_calibrator"],gate,sub);sets=bundle["conformal"].predict_set(probs);ds=decisions(rows,probs,sets,bundle["decision_parameters"]);guard.generated()
  records=[]
  for i,(r,d,p,s) in enumerate(zip(rows.itertuples(),ds,probs,sets)):
   clean={k:v for k,v in d.items() if k not in ("true_class","episode_id","variant_id","environment_group")};clean.update({"row_index":i,"execution_id":str(r.execution_id),"joint_probabilities":[float(x) for x in p],"conformal_set":[str(x) for x in s]});records.append(clean)
  payload={"candidate_id":bundle["candidate_id"],"classes":CLASSES,"record_count":len(records),"records":records};output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");report=guard.report()
 return {"immutable_prediction_created":True,"prediction_skipped_on_resume":False,"immutable_prediction_sha256":sha(output),**report}
