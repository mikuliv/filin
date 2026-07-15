"""Nested grouped selection минимальной decision policy и freeze candidate v0.3.10."""
from __future__ import annotations
import argparse, itertools, sys
from datetime import UTC, datetime
from pathlib import Path
import joblib, numpy as np, yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(HERE), str(ROOT / "ml/models"), str(ROOT / "ml/features"), str(ROOT / "ml/decision")]
from continuous_class_support import ContinuousClassSupport
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
from mondrian_conformal_classifier import MondrianConformalClassifier
from ml.experiments.v0_3_10.pipeline import *

def rank(record):
    episode, window = record["episode_metrics"], record["window_metrics"]
    latency = episode["time_to_first_alert"]["mean"] if episode["time_to_first_alert"]["mean"] is not None else 99
    return (-episode["attack_episode_recall"], -episode["detection_by_second_window"], -episode["episode_alert_precision"],
            episode["benign_episode_false_alert_rate"], window["attack_pending_rate"], window["review_rate"],
            -window["true_class_candidate_evidence_recall"], latency,
            record["parameters"].get("strong_threshold_mode") == "class_conditional",
            record["parameters"].get("weak_repetition_policy") != "two_consecutive")

def evaluate(rows, X, probabilities, conformal, support, parameters):
    decisions = evidence_decisions(rows, probabilities, conformal, support, X, parameters)
    window, episode = operational_metrics(rows, decisions)
    labels = rows.episode_class.astype(str).to_numpy(); attack = labels != "benign"; benign = ~attack
    strong = decisions.strong_attack_evidence.astype(bool).to_numpy()
    weak = decisions.weak_attack_evidence.astype(bool).to_numpy()
    correct_strong = np.array([flag and evidence == label for flag, evidence, label in zip(strong, decisions.evidence_class, labels)])
    correct_weak = np.array([flag and evidence == label for flag, evidence, label in zip(weak, decisions.evidence_class, labels)])
    evidence = correct_strong | correct_weak
    per_class = {label: float(evidence[labels == label].mean()) for label in ATTACK_CLASSES}
    return {"policy_id": "minimal:" + sha256_json(parameters)[:12], "parameters": parameters,
            "strong_alert_precision": float(correct_strong.sum() / max(strong.sum(), 1)),
            "strong_attack_window_recall": float(correct_strong[attack].mean()),
            "strong_benign_false_promotion_rate": float(strong[benign].mean()),
            "weak_evidence_precision": float(correct_weak.sum() / max(weak.sum(), 1)),
            "true_class_candidate_evidence_recall": float(evidence[attack].mean()),
            "per_class_candidate_evidence_recall": per_class,
            "window_metrics": window, "episode_metrics": episode, "decisions": decisions}

def public(record):
    return {key: value for key, value in record.items() if key != "decisions"}

def passes_training_policy(record, closed):
    e,w=record["episode_metrics"],record["window_metrics"]
    return (closed["macro_f1"]>=.90 and closed["balanced_accuracy"]>=.92 and closed["benign_recall"]>=.92 and closed["FPR"]<=.08 and closed["attack_macro_recall"]>=.92 and
      record["strong_alert_precision"]>=.97 and record["strong_attack_window_recall"]>=.35 and record["strong_benign_false_promotion_rate"]<=.02 and
      record["true_class_candidate_evidence_recall"]>=.92 and min(record["per_class_candidate_evidence_recall"].values())>=.85 and
      w["benign_recall"]>=.90 and w["benign_window_alert_emission_rate"]<=.05 and e["benign_episode_false_alert_rate"]<=.05 and
      w["pending_rate"]<=.20 and w["attack_pending_rate"]<=.20 and w["review_rate"]<=.15 and w["attack_review_rate"]<=.15 and
      e["attack_episode_recall"]>=.97 and e["episode_alert_precision"]>=.95 and e["attack_episode_unresolved_rate"]<=.03 and e["detection_by_second_window"]>=.92 and
      (e["time_to_first_alert"]["median"] or 99)<=2 and (e["time_to_first_alert"]["maximum"] or 99)<=3 and min(value["recall"] for value in e["per_class"].values())>=.90)

def class_thresholds(rows, probabilities, conformal_sets):
    labels = rows.episode_class.astype(str).to_numpy(); result, unavailable = {}, []
    for label in ATTACK_CLASSES:
        index = CLASSES.index(label); chosen = None
        for threshold, margin in itertools.product((.65,.70,.75,.80,.85,.90,.95),(.10,.20,.30)):
            order = np.sort(probabilities, axis=1)
            mask = ((probabilities.argmax(axis=1) == index) & np.array([value == [label] for value in conformal_sets]) &
                    (probabilities[:, index] >= threshold) & ((order[:, -1] - order[:, -2]) >= margin) & (probabilities[:, 0] <= .20))
            correct = mask & (labels == label); precision = correct.sum() / max(mask.sum(), 1)
            benign_false = mask[labels == "benign"].mean()
            if precision >= .97 and benign_false <= .02 and correct.sum() >= 6:
                chosen = (threshold, margin); break
        if chosen is None:
            chosen = (.95, .30); unavailable.append(label)
        result[label] = chosen[0]
    return result, max((.30 if unavailable else .10), max((.10 for _ in result), default=.10)), unavailable

def staged_selection(rows,X,probabilities,conformal,support,closed_metrics):
    sets=conformal.predict_set(probabilities)
    base={"maximum_strong_benign_probability":.20,"weak_thresholds_per_class":{label:.45 for label in ATTACK_CLASSES},
          "weak_probability_margin":0.0,"weak_benign_ceiling":.50,"weak_repetition_policy":"two_of_three",
          "pending_ttl_windows":3,"ambiguity_margin":.07,"strong_benign_probability":.80,
          "strong_benign_margin":.30,"dedup_ttl_windows":3,"diagnostic_support_affects_decision":False}
    strong=[]
    for probability,margin in itertools.product((.70,.80,.90,.95),(.10,.20,.30)):
        parameters={**base,"strong_threshold_mode":"global","strong_thresholds_per_class":{label:probability for label in ATTACK_CLASSES},"strong_probability_margin":margin}
        strong.append(evaluate(rows,X,probabilities,conformal,support,parameters))
    thresholds,margin,unavailable=class_thresholds(rows,probabilities,sets)
    strong.append(evaluate(rows,X,probabilities,conformal,support,{**base,"strong_threshold_mode":"class_conditional",
        "strong_thresholds_per_class":thresholds,"strong_probability_margin":margin,"class_strong_path_unavailable":unavailable}))
    strong_finalists=sorted(strong,key=rank)[:4];weak=[]
    for finalist in strong_finalists:
        for probability,weak_margin,repetition in itertools.product((.35,.45,.55,.65),(.00,.05),("two_consecutive","two_of_three")):
            parameters={**finalist["parameters"],"weak_thresholds_per_class":{label:probability for label in ATTACK_CLASSES},
                        "weak_probability_margin":weak_margin,"weak_repetition_policy":repetition}
            weak.append(evaluate(rows,X,probabilities,conformal,support,parameters))
    weak_finalists=sorted(weak,key=rank)[:6];final=[]
    for finalist in weak_finalists:
        for ambiguity,ttl in itertools.product((.03,.07),(2,3)):
            final.append(evaluate(rows,X,probabilities,conformal,support,{**finalist["parameters"],"ambiguity_margin":ambiguity,"pending_ttl_windows":ttl}))
    final.sort(key=rank);passing=[value for value in final if passes_training_policy(value,closed_metrics)]
    return {"strong":strong,"strong_finalists":strong_finalists,"weak":weak,"weak_finalists":weak_finalists,
            "final":final,"passing":passing,"selected":(passing or final)[0]}

def control_policies(rows, X, probabilities, conformal, support, selected):
    permissive = {label: 0.0 for label in ATTACK_CLASSES}
    direct = {**selected, "strong_thresholds_per_class": permissive, "strong_probability_margin": 0.0,
              "maximum_strong_benign_probability": 1.0, "ambiguity_margin": 0.0}
    singleton = {**direct, "strong_thresholds_per_class": permissive}
    repeated = {**selected, "strong_thresholds_per_class": {label: 2.0 for label in ATTACK_CLASSES},
                "weak_thresholds_per_class": {label: .35 for label in ATTACK_CLASSES}, "weak_repetition_policy": "two_of_three"}
    conservative = {**selected, "strong_thresholds_per_class": {label: .85 for label in ATTACK_CLASSES},
                    "weak_thresholds_per_class": {label: .55 for label in ATTACK_CLASSES}, "ambiguity_margin": .07}
    return {"control_A_direct_closed_set_upper_bound": public(evaluate(rows,X,probabilities,conformal,support,direct)),
            "control_B_conformal_singleton_direct": public(evaluate(rows,X,probabilities,conformal,support,singleton)),
            "control_C_v038_style_repeated": public(evaluate(rows,X,probabilities,conformal,support,repeated)),
            "control_D_v039_style_conservative": public(evaluate(rows,X,probabilities,conformal,support,conservative))}

def main():
    parser=argparse.ArgumentParser(description="Выбрать и заморозить minimal decision policy v0.3.10")
    parser.add_argument("--training-campaign",required=True);parser.add_argument("--protocol",required=True)
    parser.add_argument("--data-policy",required=True);parser.add_argument("--model-selection-policy",required=True)
    parser.add_argument("--output-root",required=True);parser.add_argument("--report-dir",required=True)
    parser.add_argument("--artifact-dir",required=True);parser.add_argument("--resume",action="store_true")
    args=parser.parse_args();report=ROOT/args.report_dir;artifact=ROOT/args.artifact_dir;manifest=HERE/"frozen_candidate_manifest.yaml"
    if args.resume and manifest.exists() and (report/"candidate_selection.json").exists():
        print("Decision selection и candidate freeze уже завершены; повтор не выполняется.");return
    payload=joblib.load(artifact/"grouped_oof.joblib");rows,X,oof=payload["rows"],payload["X"],payload["oof"]
    labels=rows.episode_class.astype(str).to_numpy();binary=(labels!="benign").astype(int)
    gate_cal=GroupAwareSigmoidCalibrator().fit(oof["gate_oof"],binary)
    subtype_cal=GroupAwareSigmoidCalibrator().fit(oof["subtype_oof"][binary==1],labels[binary==1])
    probabilities=calibrated_joint(gate_cal,subtype_cal,oof["gate_oof"],oof["subtype_oof"])
    conformal=MondrianConformalClassifier(.05).fit(probabilities,labels,CLASSES,source="training_oof")
    support=ContinuousClassSupport(3,.975).fit(X,labels,source="training_oof")
    selection=staged_selection(rows,X,probabilities,conformal,support,oof["metrics"])
    strong,strong_finalists,weak,weak_finalists,final,passing,selected=(selection[name] for name in ("strong","strong_finalists","weak","weak_finalists","final","passing","selected"))
    model_selection_policy_passed=bool(passing)
    controls=control_policies(rows,X,probabilities,conformal,support,selected["parameters"])
    outer=[]
    groups=rows.run_id.astype(str).to_numpy()
    outer_splitter=StratifiedGroupKFold(n_splits=6,shuffle=True,random_state=42)
    for fold,(train,test) in enumerate(outer_splitter.split(X,labels,groups),1):
        train_labels=labels[train];train_binary=binary[train];train_groups=groups[train]
        inner_gate=np.zeros(len(train));inner_subtype=np.zeros((len(train),len(ATTACK_CLASSES)));inner_audit=[]
        inner_splitter=StratifiedGroupKFold(n_splits=4,shuffle=True,random_state=42)
        for inner_fold,(inner_train,inner_test) in enumerate(inner_splitter.split(X.iloc[train],train_labels,train_groups),1):
            gate_model=make_gate("hist_gradient_boosting").fit(X.iloc[train[inner_train]],train_binary[inner_train])
            inner_gate[inner_test]=aligned_probabilities(gate_model,X.iloc[train[inner_test]],["0","1"])[:,1]
            attack_inner=inner_train[train_binary[inner_train]==1]
            subtype_model=make_subtype("hist_gradient_boosting").fit(X.iloc[train[attack_inner]],train_labels[attack_inner])
            inner_subtype[inner_test]=aligned_probabilities(subtype_model,X.iloc[train[inner_test]],ATTACK_CLASSES)
            inner_audit.append({"fold":inner_fold,"train_runs":sorted(set(train_groups[inner_train])),"test_runs":sorted(set(train_groups[inner_test])),"run_overlap":0})
        fold_gate_cal=GroupAwareSigmoidCalibrator().fit(inner_gate,train_binary)
        fold_subtype_cal=GroupAwareSigmoidCalibrator().fit(inner_subtype[train_binary==1],train_labels[train_binary==1])
        inner_probabilities=calibrated_joint(fold_gate_cal,fold_subtype_cal,inner_gate,inner_subtype)
        fold_conformal=MondrianConformalClassifier(.05).fit(inner_probabilities,train_labels,CLASSES,source="training_oof")
        fold_support=ContinuousClassSupport(3,.975).fit(X.iloc[train],train_labels,source="training_oof")
        inner_closed=closed_set_metrics(train_labels,inner_probabilities)
        fold_selection=staged_selection(rows.iloc[train].reset_index(drop=True),X.iloc[train].reset_index(drop=True),inner_probabilities,fold_conformal,fold_support,inner_closed)
        fold_parameters=fold_selection["selected"]["parameters"]
        outer_gate=make_gate("hist_gradient_boosting").fit(X.iloc[train],train_binary)
        outer_subtype=make_subtype("hist_gradient_boosting").fit(X.iloc[train[train_binary==1]],train_labels[train_binary==1])
        test_gate=aligned_probabilities(outer_gate,X.iloc[test],["0","1"])[:,1];test_subtype=aligned_probabilities(outer_subtype,X.iloc[test],ATTACK_CLASSES)
        test_probabilities=calibrated_joint(fold_gate_cal,fold_subtype_cal,test_gate,test_subtype)
        fold_result=evaluate(rows.iloc[test].reset_index(drop=True),X.iloc[test].reset_index(drop=True),test_probabilities,fold_conformal,fold_support,fold_parameters)
        outer.append({"fold":fold,"train_runs":sorted(set(groups[train])),"test_runs":sorted(set(groups[test])),"inner_folds":inner_audit,
                      "inner_selected_policy_id":fold_selection["selected"]["policy_id"],"inner_model_selection_policy_passed":bool(fold_selection["passing"]),"metrics":public(fold_result)})
    gate=make_gate("hist_gradient_boosting").fit(X,binary);subtype=make_subtype("hist_gradient_boosting").fit(X.loc[binary==1],labels[binary==1])
    bundle={"architecture_id":"network_sensor_v0_8_minimal_promotion","classes":CLASSES,"attack_classes":ATTACK_CLASSES,
            "feature_profile":CONTROL_PROFILE,"ordered_features":ordered_features(CONTROL_PROFILE),"gate":gate,"subtype":subtype,
            "gate_calibrator":gate_cal,"subtype_calibrator":subtype_cal,"conformal":conformal,"diagnostic_support":support,
            "decision_parameters":selected["parameters"]}
    artifact.mkdir(parents=True,exist_ok=True);artifact_path=artifact/"frozen_candidate.joblib";joblib.dump(bundle,artifact_path)
    campaign=yaml.safe_load((ROOT/args.training_campaign).read_text(encoding="utf-8"));oof_hash=sha256_json({"gate":oof["gate_oof"].tolist(),"subtype":oof["subtype_oof"].tolist()})
    candidate_id=selected["policy_id"]+":hgb:hgb"
    parameters=selected["parameters"]
    manifest_payload={"candidate_id":candidate_id,"architecture_id":"network_sensor_v0_8_minimal_promotion",
        "feature_profile":CONTROL_PROFILE,"feature_count":51,"ordered_feature_list":ordered_features(CONTROL_PROFILE),
        "feature_schema_sha256":schema_sha256(CONTROL_PROFILE),"feature_builder_sha256":sha256_file(ROOT/"ml/features/network_sensor_v0_6.py"),"rolling_history_depth":6,
        "gate_model":"HistGradientBoostingClassifier","gate_parameters":model_parameters("hist_gradient_boosting"),"gate_artifact_sha256":sha256_file(artifact_path),
        "subtype_model":"HistGradientBoostingClassifier","subtype_parameters":model_parameters("hist_gradient_boosting"),"subtype_artifact_sha256":sha256_file(artifact_path),
        "calibration_method":"group_aware_oof_sigmoid","gate_calibrator_parameters":gate_cal.parameters(),"subtype_calibrator_parameters":subtype_cal.parameters(),"calibration_oof_sha256":oof_hash,
        "conformal_method":"mondrian_class_conditional","conformal_alpha":.05,"conformal_class_counts":conformal.manifest()["class_calibration_counts"],"conformal_score_hashes":conformal.manifest()["class_score_hashes"],
        "diagnostic_support_method":"robust_scaler_class_conditional_nearest_neighbors","diagnostic_support_affects_decision":False,"diagnostic_support_k":3,"diagnostic_support_quantile":.975,
        **parameters,"alert_event_schema":{"immutable":True,"fields":["activity_state_key","alert_class","emitted_at","dedup_expires_at","source_path"]},
        "operational_states":["benign","observe_pending:<class>","review_required:ambiguous","review_required:novel","alert_emitted:<class>","alert_emitted:unclassified"],"classes":CLASSES,
        "training_run_ids":[row["run_id"] for row in campaign["runs"]],"training_dataset_sha256":sha256_json(labels.tolist()),
        "training_mapping_sha256":sha256_json(rows[["run_id","execution_id","episode_id","episode_phase","episode_class"]].to_dict("records")),"training_oof_sha256":oof_hash,
        "protocol_sha256":sha256_file(ROOT/args.protocol),"data_access_policy_sha256":sha256_file(ROOT/args.data_policy),"model_selection_policy_sha256":sha256_file(ROOT/args.model_selection_policy),
        "candidate_artifact":artifact_path.relative_to(ROOT).as_posix(),"candidate_frozen_at":datetime.now(UTC).isoformat(),"candidate_frozen_before_validation_collection":True,
        "model_trained_on_v036_data":False,"model_trained_on_v037_data":False,"model_trained_on_v038_data":False,"model_trained_on_v039_data":False,
        "model_selection_policy_passed":model_selection_policy_passed,"prohibit_refit_on_validation":True,"prohibit_tuning_on_validation":True}
    manifest.write_text(yaml.safe_dump(manifest_payload,allow_unicode=True,sort_keys=False),encoding="utf-8")
    write_json(report/"calibration_report.json",{"method":"group_aware_oof_sigmoid","source":"training_oof","sha256":oof_hash})
    write_json(report/"conformal_report.json",conformal.manifest());write_json(report/"diagnostic_support_report.json",{**support.manifest(),"diagnostic_support_affects_decision":False})
    write_json(report/"strong_path_selection.json",{"candidate_families":13,"global_candidates":12,"class_conditional_candidates":1,"finalists":[public(value) for value in strong_finalists]})
    write_json(report/"weak_path_selection.json",{"candidate_count":64,"finalists":[public(value) for value in weak_finalists]})
    write_json(report/"minimal_policy_selection.json",{"candidate_count":24,"total_checked":101,"passing_count":len(passing),"model_selection_policy_passed":model_selection_policy_passed,"selected":public(selected)})
    write_json(report/"ambiguity_ttl_selection.json",{"candidate_count":24,"ambiguity_margins":[.03,.07],"pending_ttls":[2,3],"selected":public(selected)})
    write_json(report/"decision_policy_candidates.json",{"strong":[public(value) for value in strong],"weak":[public(value) for value in weak],"final":[public(value) for value in final]})
    write_json(report/"control_policy_metrics.json",controls);write_json(report/"control_policy_training_metrics.json",controls)
    write_json(report/"nested_outer_fold_metrics.json",{"folds":outer});write_json(report/"nested_grouped_results.json",{"outer_splits":6,"inner_splits":4,"folds":outer})
    write_json(report/"candidate_selection.json",{"selected":public(selected),"controls":controls})
    write_json(report/"candidate_freeze_audit.json",{"candidate_frozen":True,"candidate_frozen_before_validation_collection":True,
        "candidate_artifact_sha256":sha256_file(artifact_path),"candidate_manifest_sha256":sha256_file(manifest)})
    print(f"Выбран и заморожен candidate {candidate_id}")

if __name__=="__main__":main()
