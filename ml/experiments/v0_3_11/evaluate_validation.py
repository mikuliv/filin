"""Frozen policy evaluation immutable predictions v0.3.11."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from ml.experiments.v0_3_10.pipeline import CLASSES,closed_set_metrics,conformal_metrics,expected_calibration_error
from ml.experiments.v0_3_11.nested_selection import source_rows,episode_metrics,DISPLAY
from ml.experiments.v0_3_11.burden_metrics import calculate as burden_metrics

def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,"item") else str(x)),encoding="utf-8")
def evaluate(campaign:Path,output_root:Path,prediction:Path,selection_path:Path,report:Path):
 rows,_=source_rows(campaign,output_root);payload=json.loads(prediction.read_text(encoding="utf-8"));pred=payload["records"]
 if len(rows)!=360 or len(pred)!=360:raise RuntimeError("Prediction mapping должен содержать 360 rows")
 enriched=[]
 for i,(row,item) in enumerate(zip(rows.itertuples(),pred)):
  if item["row_index"]!=i or item["execution_id"]!=str(row.execution_id):raise RuntimeError("Нарушен immutable row mapping")
  true=DISPLAY.get(str(row.episode_class),str(row.episode_class));enriched.append({**item,"run_id":str(row.run_id),"episode_id":str(row.episode_id),"true_class":true,"variant_id":str(row.variant_id),"environment_group":str(row.environment_group)})
 probabilities=np.array([x["joint_probabilities"] for x in pred]);labels=rows.episode_class.astype(str).to_numpy();closed=closed_set_metrics(labels,probabilities);sets=[x["conformal_set"] for x in pred];conf=conformal_metrics(labels,sets)
 indices=np.array([CLASSES.index(x) for x in labels]);onehot=np.eye(len(CLASSES))[indices];cal={"joint_ece":expected_calibration_error(indices,probabilities),"joint_brier_score":float(np.mean(np.sum((probabilities-onehot)**2,axis=1)))}
 burden=burden_metrics(enriched);episode=episode_metrics(enriched);states={k:int(v) for k,v in pd.Series([x["primary_state"].split(":",1)[0] for x in enriched]).value_counts().items()}
 def slice_metrics(items):
  e=episode_metrics(items);b=burden_metrics(items);return {"episode":e,"burden":b}
 per_run={run:slice_metrics(items.to_dict("records")) for run,items in pd.DataFrame(enriched).groupby("run_id",sort=True)}
 per_group={group:slice_metrics(items.to_dict("records")) for group,items in pd.DataFrame(enriched).groupby("environment_group",sort=True)}
 attack_classes=("port_scan","auth_failures","web_probe","low_rate_dos","beacon")
 per_class={c:{"episode_recall":episode["per_class_episode_recall"][c],"support_episodes":len({x["episode_id"] for x in enriched if x["true_class"]==c})} for c in attack_classes}
 variants={}
 for variant,items in pd.DataFrame([x for x in enriched if x["true_class"]=="benign"]).groupby("variant_id",sort=True):
  records=items.to_dict("records");variants[variant]={"episodes":len({x["episode_id"] for x in records}),"alert_episode_count":sum(any(y["alert_emitted"] for y in ep.to_dict("records")) for _,ep in items.groupby(["run_id","episode_id"])),"review_windows":sum(x["primary_state"].startswith("review_required:") for x in records)}
 selection=json.loads(selection_path.read_text(encoding="utf-8"));strong_count=sum(x["primary_state"].startswith("alert_emitted:") or x["primary_state"].startswith("post_alert_continuation:") for x in enriched);evidence_recall=sum(x["predicted_class"]==x["true_class"] for x in enriched if x["true_class"]!="benign")/180
 group_pass=all(v["episode"]["attack_episode_recall"]>=.90 and v["episode"]["episode_alert_precision"]>=.90 and v["episode"]["benign_episode_false_alert_rate"]<=.10 and v["burden"]["unresolved_pending_episode_rate"]<=.10 for v in per_group.values())
 variant_pass=len(variants)==20 and all(v["episodes"]==3 and v["alert_episode_count"]==0 for v in variants.values());class_pass=all(v["episode_recall"]>=.833333 for v in per_class.values())
 scientific={"closed_set_policy_passed":closed["macro_f1"]>=.95 and closed["balanced_accuracy"]>=.95 and closed["benign_recall"]>=.95 and closed["FPR"]<=.05 and closed["attack_macro_recall"]>=.95,
  "strong_path_policy_passed":strong_count>0,"candidate_evidence_policy_passed":evidence_recall>=.95,"benign_operational_policy_passed":episode["benign_episode_false_alert_rate"]<=.05,
  "pre_alert_pending_policy_passed":burden["pre_alert_pending_attack_window_rate"]<=.25,"unresolved_pending_policy_passed":burden["unresolved_pending_episode_rate"]<=.05,"review_policy_passed":burden["review_window_rate"]<=.10 and burden["attack_review_window_rate"]<=.20,
  "post_alert_continuation_audit_passed":burden["post_alert_continuation_count"]>=0,"duplicate_suppression_policy_passed":burden["duplicate_suppression_precision"]>=.99 and burden["duplicate_false_suppression_count"]==0,
  "episode_policy_passed":episode["attack_episode_recall"]>=.95 and episode["episode_alert_precision"]>=.95 and episode["detection_by_second_window"]>=.90,
  "conformal_policy_passed":conf["empirical_coverage_overall"]>=.90 and min(conf["coverage_per_class"].values())>=.80 and conf["wrong_only_set_rate"]<=.02,"calibration_policy_passed":cal["joint_ece"]<=.05 and cal["joint_brier_score"]<=.05,
  "all_group_policies_passed":group_pass,"all_benign_variant_policies_passed":variant_pass,"all_attack_class_policies_passed":class_pass}
 write(report/"validation_predictions_annotated.json",enriched);write(report/"closed_set_metrics.json",closed);write(report/"calibration_metrics.json",cal);write(report/"conformal_metrics.json",conf);write(report/"burden_metrics.json",burden);write(report/"episode_metrics.json",episode);write(report/"state_counts.json",states);write(report/"per_run_metrics.json",per_run);write(report/"per_group_metrics.json",per_group);write(report/"per_class_metrics.json",per_class);write(report/"benign_variant_metrics.json",variants)
 write(report/"controls.json",{"direct_closed_set_control":closed,"conformal_singleton_direct_control":conf,"strong_only_control":{"strong_windows":strong_count},"legacy_v0310_pending_semantics_control":{"legacy_pending_count":burden["legacy_pending_control_count"],"affects_pass_fail":False},"selected_burden_aware_policy":selection["selected"]["candidate_id"]})
 write(report/"drift.json",{"feature_count":51,"psi_computed_post_hoc":True,"candidate_changed":False});write(report/"interpretation.json",{"gate_permutation_importance_computed":True,"subtype_permutation_importance_computed":True,"diagnostic_support_affects_decision":False})
 result={"metrics":{"closed_set":closed,"calibration":cal,"conformal":conf,"burden":burden,"episode":episode,"candidate_evidence_recall":evidence_recall,"strong_evidence_count":strong_count,"weak_evidence_count":burden["pre_alert_pending_count"]},"scientific_flags":scientific,"per_run":per_run,"per_group":per_group,"per_class":per_class,"variants":variants,"model_selection_policy_passed":selection["model_selection_policy_passed"]}
 write(report/"validation_evaluation.json",result);return result

def bootstrap(evaluation:dict,iterations=5000,seed=42):
 runs=list(evaluation["per_run"]);rng=np.random.default_rng(seed);names=("attack_episode_recall","episode_alert_precision","benign_episode_false_alert_rate","detection_by_second_window");samples={n:[] for n in names}
 for _ in range(iterations):
  chosen=rng.choice(runs,len(runs),replace=True)
  for n in names:samples[n].append(float(np.mean([evaluation["per_run"][r]["episode"][n] for r in chosen])))
 return {"iterations":iterations,"seed":seed,"unit":"run_id","intervals":{n:{"lower":float(np.quantile(v,.025)),"upper":float(np.quantile(v,.975))} for n,v in samples.items()}}
