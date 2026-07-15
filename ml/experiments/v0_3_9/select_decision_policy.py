"""Staged training-only selection и freeze episode-first candidate."""
from __future__ import annotations
import argparse,itertools,sys,json,hashlib
from datetime import UTC,datetime
from pathlib import Path
import joblib,numpy as np,yaml
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(ROOT/"ml/models"),str(ROOT/"ml/features")]
from continuous_class_support import ContinuousClassSupport
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
from mondrian_conformal_classifier import MondrianConformalClassifier
from pipeline import *

def rank(record):
 e=record["episode_metrics"];w=record["window_metrics"]
 return (-e["attack_episode_recall"],e["benign_episode_false_alert_rate"],-e["episode_alert_precision"],-e["detection_by_first_window"],-e["detection_by_second_window"],w["attack_review_rate"],e["time_to_first_alert"]["median"] or 99)
def evaluate(rows,X,probabilities,conformal,support,parameters):
 decisions=evidence_decisions(rows,probabilities,conformal,support,X,parameters);window,episode=operational_metrics(rows,decisions);labels=rows.episode_class.astype(str).to_numpy()
 strong=np.array(decisions.strong_attack_evidence,bool);attack=labels!="benign";correct=np.array([bool(flag and row.top_class==label) for flag,row,label in zip(strong,decisions.itertuples(),labels)])
 return {"policy_id":"decision:"+sha256_json(parameters)[:12],"parameters":parameters,"strong_evidence_precision":float(correct.sum()/max(strong.sum(),1)),"strong_evidence_recall":float(correct[attack].mean()),"window_metrics":window,"episode_metrics":episode,"decisions":decisions}
def public(record):return {k:v for k,v in record.items() if k!="decisions"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--training-campaign",required=True);p.add_argument("--protocol",required=True);p.add_argument("--data-policy",required=True);p.add_argument("--model-selection-policy",required=True);p.add_argument("--output-root",required=True);p.add_argument("--report-dir",required=True);p.add_argument("--artifact-dir",required=True);p.add_argument("--resume",action="store_true");a=p.parse_args()
 report=ROOT/a.report_dir;artifact=ROOT/a.artifact_dir;manifest=HERE/"frozen_candidate_manifest.yaml"
 if a.resume and manifest.exists() and (report/"candidate_selection.json").exists():print("Decision selection и candidate freeze уже завершены; повтор не выполняется.");return
 payload=joblib.load(artifact/"grouped_oof.joblib");rows,X,oof=payload["rows"],payload["X"],payload["oof"];labels=rows.episode_class.astype(str).to_numpy();binary=(labels!="benign").astype(int)
 gate_cal=GroupAwareSigmoidCalibrator().fit(oof["gate_oof"],binary);sub_cal=GroupAwareSigmoidCalibrator().fit(oof["subtype_oof"][binary==1],labels[binary==1]);probabilities=calibrated_joint(gate_cal,sub_cal,oof["gate_oof"],oof["subtype_oof"])
 conformal=MondrianConformalClassifier(.05).fit(probabilities,labels,CLASSES,source="training_oof");support=ContinuousClassSupport(3,.975).fit(X,labels,source="training_oof")
 base={"maximum_strong_benign_probability":.10,"weak_attack_probability":.45,"weak_repeat_policy":"consistent_2_of_3","decay":.7,"activation_threshold":1.2,"strong_benign_reset_probability":.8}
 strong=[]
 for probability,margin,ratio in itertools.product((.85,.90),(.40,.55),(.90,1.0)):
  parameters={**base,"strong_attack_probability":probability,"strong_probability_margin":margin,"strong_support_ratio":ratio};strong.append(evaluate(rows,X,probabilities,conformal,support,parameters))
 strong_finalists=sorted(strong,key=rank)[:2];weak=[]
 for finalist in strong_finalists:
  for probability,repeat in itertools.product((.45,.60),("consistent_2_of_3","consistent_2_of_4")):
   parameters={**finalist["parameters"],"weak_attack_probability":probability,"weak_repeat_policy":repeat};weak.append(evaluate(rows,X,probabilities,conformal,support,parameters))
 weak_finalists=sorted(weak,key=rank)[:4];final=[]
 for finalist in weak_finalists:
  for decay,threshold,benign in itertools.product((.5,.7),(1.2,1.6),(.8,.9)):
   parameters={**finalist["parameters"],"decay":decay,"activation_threshold":threshold,"strong_benign_reset_probability":benign};final.append(evaluate(rows,X,probabilities,conformal,support,parameters))
 final.sort(key=rank);selected=final[0]
 control_parameters={**base,"strong_attack_probability":2.0,"strong_probability_margin":1.0,"strong_support_ratio":0.0,"weak_attack_probability":.45,"weak_repeat_policy":"consistent_2_of_3","decay":.7,"activation_threshold":1.6,"strong_benign_reset_probability":.8};control=evaluate(rows,X,probabilities,conformal,support,control_parameters)
 gate=make_gate("hist_gradient_boosting").fit(X,binary);subtype=make_subtype("hist_gradient_boosting").fit(X.loc[binary==1],labels[binary==1])
 bundle={"architecture_id":"network_sensor_v0_7_episode_first","classes":CLASSES,"attack_classes":ATTACK_CLASSES,"feature_profile":CONTROL_PROFILE,"ordered_features":ordered_features(CONTROL_PROFILE),"gate":gate,"subtype":subtype,"gate_calibrator":gate_cal,"subtype_calibrator":sub_cal,"conformal":conformal,"support":support,"decision_parameters":selected["parameters"]}
 artifact_path=artifact/"frozen_candidate.joblib";joblib.dump(bundle,artifact_path);campaign=yaml.safe_load((ROOT/a.training_campaign).read_text(encoding="utf-8"));oof_hash=sha256_json({"gate":oof["gate_oof"].tolist(),"subtype":oof["subtype_oof"].tolist()})
 candidate_id=selected["policy_id"]+":hgb:hgb";m={"candidate_id":candidate_id,"architecture_id":"network_sensor_v0_7_episode_first","feature_profile":CONTROL_PROFILE,"feature_count":51,"ordered_feature_list":ordered_features(CONTROL_PROFILE),"feature_schema_sha256":schema_sha256(CONTROL_PROFILE),"feature_builder_sha256":sha256_file(ROOT/"ml/features/network_sensor_v0_6.py"),"rolling_history_depth":6,"gate_model":"HistGradientBoostingClassifier","gate_parameters":model_parameters("hist_gradient_boosting"),"gate_artifact_sha256":sha256_file(artifact_path),"subtype_model":"HistGradientBoostingClassifier","subtype_parameters":model_parameters("hist_gradient_boosting"),"subtype_artifact_sha256":sha256_file(artifact_path),"calibration_method":"group_aware_oof_sigmoid","gate_calibrator_parameters":gate_cal.parameters(),"subtype_calibrator_parameters":sub_cal.parameters(),"calibration_oof_sha256":oof_hash,"conformal_method":"mondrian_class_conditional","conformal_alpha":.05,"conformal_class_counts":conformal.manifest()["class_calibration_counts"],"conformal_score_hashes":conformal.manifest()["class_score_hashes"],"support_method":"robust_scaler_class_conditional_nearest_neighbors","support_k":3,"support_quantile":.975,"support_class_thresholds":support.thresholds_,"support_scaler_sha256":support.manifest()["sha256"],"support_artifact_sha256":sha256_file(artifact_path),**selected["parameters"],"signed_evidence_weights":{"probability":.5,"conformal":.2,"probability_margin":.15,"support_margin":.15},"active_minimum_hold_windows":2,"state_ttl_windows":3,"inactivity_reset_policy":"timestamp_gap","decision_states":["observing","pending","active","review","cooldown"],"lifecycle_states":["observing","pending:<class>","active:<class>","active:unclassified","review:novel","review:ambiguous","review:weak","cooldown:<class>"],"classes":CLASSES,"training_run_ids":[r["run_id"] for r in campaign["runs"]],"training_dataset_sha256":sha256_json(labels.tolist()),"training_mapping_sha256":sha256_json(rows[["run_id","execution_id","episode_id","episode_phase","episode_class"]].to_dict("records")),"training_oof_sha256":oof_hash,"protocol_sha256":sha256_file(ROOT/a.protocol),"data_access_policy_sha256":sha256_file(ROOT/a.data_policy),"model_selection_policy_sha256":sha256_file(ROOT/a.model_selection_policy),"candidate_artifact":artifact_path.relative_to(ROOT).as_posix(),"candidate_frozen_at":datetime.now(UTC).isoformat(),"candidate_frozen_before_validation_collection":True,"model_trained_on_v036_data":False,"model_trained_on_v037_data":False,"model_trained_on_v038_data":False,"prohibit_refit_on_validation":True,"prohibit_tuning_on_validation":True}
 manifest.write_text(yaml.safe_dump(m,allow_unicode=True,sort_keys=False),encoding="utf-8")
 comparison={name:selected["episode_metrics"].get(name,selected["window_metrics"].get(name,0))-control["episode_metrics"].get(name,control["window_metrics"].get(name,0)) for name in ("attack_episode_recall","episode_alert_precision","benign_episode_false_alert_rate","detection_by_first_window","detection_by_second_window","review_rate","attack_review_rate")}
 write_json(report/"calibration_report.json",{"method":"group_aware_oof_sigmoid","source":"training_oof","sha256":oof_hash});write_json(report/"conformal_report.json",conformal.manifest());write_json(report/"continuous_support_report.json",support.manifest());write_json(report/"control_policy_metrics.json",public(control));write_json(report/"strong_gate_selection.json",{"candidate_count":8,"finalists":[public(x) for x in strong_finalists]});write_json(report/"weak_evidence_selection.json",{"candidate_count":8,"finalists":[public(x) for x in weak_finalists]});write_json(report/"signed_evidence_selection.json",{"candidate_count":32,"finalists":[public(x) for x in final]});write_json(report/"lifecycle_selection.json",{"candidate_count":32,"selected":public(selected)});write_json(report/"decision_policy_candidates.json",{"strong":[public(x) for x in strong],"weak":[public(x) for x in weak],"final":[public(x) for x in final]});write_json(report/"candidate_selection.json",{"selected":public(selected),"control_comparison":comparison});write_json(report/"candidate_freeze_audit.json",{"candidate_frozen":True,"candidate_frozen_before_validation_collection":True,"candidate_artifact_sha256":sha256_file(artifact_path),"candidate_manifest_sha256":sha256_file(manifest)})
 print(f"Выбран и заморожен candidate {candidate_id}")
if __name__=="__main__":main()
