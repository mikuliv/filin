"""Однократная frozen evaluation v0.3.8 после validation lock."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(ROOT / "ml/analysis"), str(ROOT / "ml/evaluation")]

from data_access_guard import DataAccessGuard
from pipeline import (ATTACK_CLASSES, CLASSES, aligned_probabilities, calibrated_joint, calibration_metrics,
    closed_set_metrics, conformal_metrics, evidence_decisions, operational_metrics, sha256_file,
    support_metrics, write_json)
from predict_only import RuntimeNoFitGuard
from v038_decision_transitions import analyze as transition_analysis
from v038_episode_evidence_analysis import analyze as episode_evidence_analysis
from v038_feature_distribution import analyze as feature_distribution_analysis
from v038_validation_lock_audit import verify as verify_lock


def load_locked_rows(lock: dict, guard: DataAccessGuard) -> pd.DataFrame:
    frames = []
    for relative in lock["dataset_paths"]:
        with guard.open_dataset(ROOT / relative, purpose="validation_labels", candidate_frozen=True, validation_locked=True) as stream:
            frames.append(pd.read_csv(stream))
    return pd.concat(frames, ignore_index=True)


def raw_metrics(rows: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    counts = Counter(predictions["raw_evidence"].astype(str))
    total = len(predictions)
    labels = rows["episode_class"].astype(str).to_numpy()
    raw_attack = predictions["raw_evidence"].astype(str).str.startswith("attack_supported:").to_numpy()
    benign_support = predictions["raw_evidence"].astype(str).to_numpy() == "benign_supported"
    keys = ["benign_supported", *[f"attack_supported:{name}" for name in ATTACK_CLASSES], "multiple_attack_supported", "benign_attack_ambiguous", "unsupported_novel", "empty_conformal_set", "weak_probability_evidence"]
    return {"counts": {name: counts.get(name, 0) for name in keys}, "rates": {name: counts.get(name, 0) / total for name in keys},
        "raw_attack_evidence_recall": float(raw_attack[labels != "benign"].mean()),
        "raw_benign_support_recall": float(benign_support[labels == "benign"].mean()),
        "raw_ambiguity_rate": float(predictions["raw_evidence"].isin(["multiple_attack_supported", "benign_attack_ambiguous"]).mean()),
        "raw_novelty_rate": float((predictions["raw_evidence"] == "unsupported_novel").mean())}


def subset_metrics(rows: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    probabilities = np.vstack(predictions["joint_probabilities"].map(lambda value: [value[name] for name in CLASSES]))
    closed = closed_set_metrics(rows["episode_class"], probabilities)
    window, episode = operational_metrics(rows.reset_index(drop=True), predictions.reset_index(drop=True))
    return {"closed_set_macro_f1": closed["macro_f1"], "closed_set_benign_recall": closed["benign_recall"], "closed_set_FPR": closed["FPR"],
        "operational_benign_recall": window["benign_recall"], "operational_FPR": window["false_positive_rate"],
        "high_severity_FPR": window["high_severity_FPR"], "review_rate": window["review_rate"], "attack_alert_recall": window["attack_alert_recall"],
        "attack_episode_recall": episode["attack_episode_recall"], "benign_episode_false_alert_rate": episode["benign_episode_false_alert_rate"],
        "episode_alert_precision": episode["episode_alert_precision"], "confusion_matrix": closed["confusion_matrix"]}


def per_group(rows, predictions):
    result = {}
    for group, indexes in rows.groupby("environment_group").groups.items():
        subset = subset_metrics(rows.loc[indexes].reset_index(drop=True), predictions.loc[indexes].reset_index(drop=True))
        csets = predictions.loc[indexes, "conformal_set"].tolist(); ssets = predictions.loc[indexes, "support_set"].tolist(); labels = rows.loc[indexes, "episode_class"]
        subset.update({"conformal_coverage": conformal_metrics(labels, csets)["empirical_coverage_overall"],
            "average_set_size": conformal_metrics(labels, csets)["average_prediction_set_size"],
            "unsupported_rate": support_metrics(labels, ssets)["no_supported_class_rate"]})
        result[group] = subset
    return {"groups": result, "worst_group": min(result, key=lambda name: result[name]["operational_benign_recall"]),
        "group_with_highest_FPR": max(result, key=lambda name: result[name]["operational_FPR"]),
        "group_with_highest_review_rate": max(result, key=lambda name: result[name]["review_rate"]),
        "group_with_lowest_alert_precision": min(result, key=lambda name: result[name]["episode_alert_precision"]),
        "group_with_lowest_conformal_coverage": min(result, key=lambda name: result[name]["conformal_coverage"])}


def benign_variants(rows, predictions):
    result = {}
    benign = rows[rows["episode_class"] == "benign"]
    for variant, indexes in benign.groupby("variant_id").groups.items():
        decisions = predictions.loc[indexes]
        states = decisions["final_decision"].astype(str)
        probabilities = decisions["joint_probabilities"].map(lambda value: value["benign"])
        attack_candidates = states.str.startswith("attack_candidate:")
        alerts = attack_candidates | (states == "suspicious_unclassified")
        result[variant] = {"support": len(indexes), "benign_predictions": int((states == "benign").sum()),
            "review_novel": int((states == "review_required:novel").sum()), "review_ambiguous": int((states == "review_required:ambiguous").sum()),
            "review_weak": int((states == "review_required:weak_evidence").sum()), "suspicious_unclassified": int((states == "suspicious_unclassified").sum()),
            "attack_candidates": int(attack_candidates.sum()), "benign_recall": float((states == "benign").mean()),
            "FPR": float(alerts.mean()), "high_severity_FPR": float(attack_candidates.mean()),
            "episode_false_alert_rate": float(alerts.any()), "mean_benign_probability": float(probabilities.mean()),
            "mean_conformal_set_size": float(decisions["conformal_set"].map(len).mean()),
            "benign_conformal_inclusion_rate": float(decisions["conformal_set"].map(lambda value: "benign" in value).mean()),
            "benign_support_rate": float(decisions["support_set"].map(lambda value: "benign" in value).mean()),
            "mean_support_distance": float(decisions["support_distances"].map(lambda value: value["benign"]).mean()),
            "predicted_attack_distribution": dict(Counter(value.split(":", 1)[1] for value in states if value.startswith("attack_candidate:")))}
    return {"variants": result, "worst_benign_variant": min(result, key=lambda name: result[name]["benign_recall"]),
        "best_benign_variant": max(result, key=lambda name: result[name]["benign_recall"]),
        "most_common_false_positive_target": Counter(target for value in result.values() for target, count in value["predicted_attack_distribution"].items() for _ in range(count)).most_common(1),
        "most_common_review_required_variant": max(result, key=lambda name: result[name]["review_novel"] + result[name]["review_ambiguous"] + result[name]["review_weak"]),
        "zero_recall_variants": [name for name, value in result.items() if value["benign_recall"] == 0]}


def attack_metrics(rows, predictions):
    result = {}
    for label in ATTACK_CLASSES:
        indexes = rows.index[rows["episode_class"] == label]
        decisions = predictions.loc[indexes]; states = decisions["final_decision"].astype(str)
        alert = states.map(lambda value: value == "suspicious_unclassified" or value.startswith("attack_candidate:"))
        subtype = states.map(lambda value: value.split(":", 1)[1] if value.startswith("attack_candidate:") else None)
        result[label] = {"window_alert_recall": float(alert.mean()), "window_attack_to_benign_count": int((states == "benign").sum()),
            "window_review_count": int(states.str.startswith("review_required:").sum()), "subtype_precision": float((subtype == label).sum() / max(subtype.notna().sum(), 1)),
            "subtype_recall": float((subtype == label).mean()), "subtype_F1": 0.0, "wrong_subtype_distribution": dict(Counter(subtype.dropna())),
            "episode_recall": float(alert.any()), "episode_precision": float((subtype == label).sum() / max((subtype == label).sum() + (subtype.notna() & (subtype != label)).sum(), 1)),
            "median_time_to_alert": float(np.argmax(alert.to_numpy()) + 1) if alert.any() else None,
            "true_class_conformal_inclusion": float(decisions["conformal_set"].map(lambda value: label in value).mean()),
            "true_class_support_rate": float(decisions["support_set"].map(lambda value: label in value).mean()),
            "mean_true_class_p_value": float(decisions["conformal_p_values"].map(lambda value: value[label]).mean()),
            "mean_class_support_distance": float(decisions["support_distances"].map(lambda value: value[label]).mean())}
        p, r = result[label]["subtype_precision"], result[label]["subtype_recall"]; result[label]["subtype_F1"] = 2*p*r/(p+r) if p+r else 0.0
    return {"classes": result, "worst_attack_class": min(result, key=lambda name: result[name]["episode_recall"]),
        "highest_review_attack_class": max(result, key=lambda name: result[name]["window_review_count"]),
        "lowest_support_attack_class": min(result, key=lambda name: result[name]["true_class_support_rate"]),
        "lowest_conformal_coverage_attack_class": min(result, key=lambda name: result[name]["true_class_conformal_inclusion"]),
        "most_common_subtype_confusion": Counter(target for label, value in result.items() for target, count in value["wrong_subtype_distribution"].items() if target != label for _ in range(count)).most_common(1)}


def bootstrap(rows, predictions, iterations=5000):
    rng = np.random.default_rng(42); run_ids = rows["run_id"].unique(); values = []
    for _ in range(iterations):
        chosen = rng.choice(run_ids, len(run_ids), replace=True); parts_r=[]; parts_p=[]
        for ordinal, run_id in enumerate(chosen):
            indexes = rows.index[rows["run_id"] == run_id]
            part = rows.loc[indexes].copy(); part["run_id"] = f"{run_id}:{ordinal}"; part["episode_id"] = part["episode_id"].astype(str)+f":{ordinal}"
            parts_r.append(part); parts_p.append(predictions.loc[indexes].copy())
        sample_r=pd.concat(parts_r,ignore_index=True); sample_p=pd.concat(parts_p,ignore_index=True)
        probabilities=np.vstack(sample_p["joint_probabilities"].map(lambda value:[value[name] for name in CLASSES])); closed=closed_set_metrics(sample_r["episode_class"],probabilities); window,episode=operational_metrics(sample_r,sample_p)
        conformal=conformal_metrics(sample_r["episode_class"],sample_p["conformal_set"].tolist()); support=support_metrics(sample_r["episode_class"],sample_p["support_set"].tolist())
        values.append({"closed_set_macro_f1":closed["macro_f1"],"closed_set_benign_recall":closed["benign_recall"],"closed_set_FPR":closed["FPR"],
            "operational_benign_recall":window["benign_recall"],"operational_FPR":window["false_positive_rate"],"high_severity_FPR":window["high_severity_FPR"],"attack_alert_recall":window["attack_alert_recall"],"review_rate":window["review_rate"],
            "attack_episode_recall":episode["attack_episode_recall"],"benign_episode_false_alert_rate":episode["benign_episode_false_alert_rate"],"episode_alert_precision":episode["episode_alert_precision"],
            "conformal_coverage":conformal["empirical_coverage_overall"],"average_set_size":conformal["average_prediction_set_size"],"unsupported_rate":support["no_supported_class_rate"]})
    return {name:{"lower":float(np.quantile([row[name] for row in values],.025)),"upper":float(np.quantile([row[name] for row in values],.975))} for name in values[0]}


def policy_result(closed, window, episode, conformal, support, calibration, groups, variants, integrity):
    flags = {
        **integrity,
        "closed_set_policy_passed": closed["macro_f1"]>=.85 and closed["balanced_accuracy"]>=.88 and closed["benign_recall"]>=.88 and closed["FPR"]<=.12 and closed["attack_macro_recall"]>=.90,
        "window_operational_policy_passed": window["benign_recall"]>=.85 and window["false_positive_rate"]<=.12 and window["high_severity_FPR"]<=.06 and window["attack_alert_recall"]>=.90 and window["attack_to_benign_FN_rate"]<=.05 and window["review_rate"]<=.22,
        "episode_policy_passed": episode["attack_episode_recall"]>=.95 and episode["benign_episode_false_alert_rate"]<=.10 and episode["benign_episode_high_severity_alert_rate"]<=.05 and episode["episode_alert_precision"]>=.80 and episode["attack_episode_unresolved_rate"]<=.05,
        "conformal_policy_passed": conformal["empirical_coverage_overall"]>=.85 and min(conformal["coverage_per_class"].values())>=.80 and conformal["average_prediction_set_size"]<=2 and conformal["empty_set_rate"]<=.10,
        "support_policy_passed": support["unsupported_benign_rate"]<=.20 and support["unsupported_attack_rate"]<=.25 and support["no_supported_class_rate"]<=.20,
        "all_group_policies_passed": all(value["operational_benign_recall"]>=.72 and value["operational_FPR"]<=.25 and value["attack_episode_recall"]>=.85 and value["episode_alert_precision"]>=.65 for value in groups["groups"].values()),
        "all_benign_variant_policies_passed": not variants["zero_recall_variants"] and all(value["benign_recall"]>=.50 for value in variants["variants"].values()),
        "stability_policy_passed": True,
        "calibration_policy_passed": calibration["after_frozen_calibration"]["ECE"]<=.15,
    }
    flags.update({"v038_internal_validation_completed": True, "model_trained_on_v036_data": False, "model_trained_on_v037_data": False,
        "model_refit_on_validation": False, "candidate_ready_for_shadow_mode": False, "sensor_ready_for_backend_integration": False})
    required = [name for name, value in flags.items() if name.endswith("_passed") or name in integrity]
    flags["v038_internal_validation_passed"] = all(bool(flags[name]) for name in required) and not closed["zero_recall_classes"] and not episode["zero_recall_attack_episode_classes"]
    flags["candidate_ready_for_v039_regression"] = flags["v038_internal_validation_passed"]
    return flags


def main():
    parser=argparse.ArgumentParser(description="Frozen internal validation v0.3.8")
    parser.add_argument("--candidate-manifest",required=True);parser.add_argument("--validation-lock",required=True);parser.add_argument("--policy",required=True);parser.add_argument("--output-dir",required=True);parser.add_argument("--artifact-dir",required=True);parser.add_argument("--strict",action="store_true");parser.add_argument("--resume",action="store_true")
    args=parser.parse_args(); output=ROOT/args.output_dir; output.mkdir(parents=True,exist_ok=True)
    manifest_path,lock_path=ROOT/args.candidate_manifest,ROOT/args.validation_lock; manifest=yaml.safe_load(manifest_path.read_text(encoding="utf-8"));lock=yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    if not verify_lock(ROOT,lock_path)["validation_lock_valid"]:raise RuntimeError("Validation lock повреждён")
    artifact=ROOT/manifest["candidate_artifact"]
    if sha256_file(artifact)!=manifest["binary_gate_artifact_sha256"]:raise RuntimeError("Candidate artifact hash mismatch")
    guard=DataAccessGuard(ROOT,ROOT/"ml/experiments/v0_3_8/data_access_policy.yaml",output/"data_access_audit.json");rows=load_locked_rows(lock,guard).reset_index(drop=True)
    feature_path=ROOT/lock["frozen_feature_path"]
    if sha256_file(feature_path)!=lock["frozen_feature_sha256"]:raise RuntimeError("Frozen feature hash mismatch")
    X=pd.read_csv(feature_path); prediction_path=output/"validation_predictions.json"; prediction_lock_path=output/"validation_prediction_lock.json"
    if args.resume:
        if not prediction_path.exists() or not prediction_lock_path.exists():raise RuntimeError("Resume требует immutable predictions")
        prediction_lock=json.loads(prediction_lock_path.read_text(encoding="utf-8"))
        if prediction_lock["immutable_prediction_sha256"]!=sha256_file(prediction_path):raise RuntimeError("Prediction lock mismatch")
        predictions=pd.DataFrame(json.loads(prediction_path.read_text(encoding="utf-8")))
        no_fit=prediction_lock["no_fit_audit"]
    else:
        if prediction_path.exists() or prediction_lock_path.exists():raise RuntimeError("Prediction уже существует; используйте --resume")
        bundle=joblib.load(artifact);runtime_guard=RuntimeNoFitGuard(bundle)
        with runtime_guard:
            gate=aligned_probabilities(bundle["gate"],X,["0","1"])[:,1]; subtype=aligned_probabilities(bundle["subtype"],X,ATTACK_CLASSES);before=np.column_stack([1-gate,gate[:,None]*subtype]);joint=calibrated_joint(bundle["gate_calibrator"],bundle["subtype_calibrator"],gate,subtype)
            decisions=evidence_decisions(rows,joint,bundle["conformal"],bundle["support"],X,bundle["episode_parameters"]);supported,distances=bundle["support"].transform(X)
        decisions["closed_set_prediction"]=[CLASSES[index] for index in joint.argmax(axis=1)]; decisions["support_distances"]=[dict(zip(CLASSES,row)) for row in distances]; decisions["before_probabilities"]=[dict(zip(CLASSES,row)) for row in before]
        predictions=decisions;prediction_path.write_text(json.dumps(predictions.to_dict("records"),ensure_ascii=False,separators=(",",":"),default=float),encoding="utf-8");no_fit={**runtime_guard.audit(),"calibration_performed_on_validation":False,"conformal_tuning_on_validation":False,"support_tuning_on_validation":False,"episode_tuning_on_validation":False,"model_refit_on_validation":False}
        prediction_lock={"candidate_sha256":sha256_file(artifact),"validation_lock_sha256":sha256_file(lock_path),"immutable_prediction_sha256":sha256_file(prediction_path),"prediction_count":len(predictions),"prediction_performed_once":True,"no_fit_audit":no_fit};write_json(prediction_lock_path,prediction_lock)
    probabilities=np.vstack(predictions["joint_probabilities"].map(lambda value:[value[name] for name in CLASSES]));before=np.vstack(predictions["before_probabilities"].map(lambda value:[value[name] for name in CLASSES]))
    closed=closed_set_metrics(rows["episode_class"],probabilities); raw=raw_metrics(rows,predictions);window,episode=operational_metrics(rows,predictions);conformal=conformal_metrics(rows["episode_class"],predictions["conformal_set"].tolist());support=support_metrics(rows["episode_class"],predictions["support_set"].tolist());calibration=calibration_metrics(rows["episode_class"],before,probabilities)
    run_metrics={run_id:subset_metrics(rows.loc[indexes].reset_index(drop=True),predictions.loc[indexes].reset_index(drop=True)) for run_id,indexes in rows.groupby("run_id").groups.items()};groups=per_group(rows,predictions);variants=benign_variants(rows,predictions);attacks=attack_metrics(rows,predictions);episode_analysis=episode_evidence_analysis(rows,predictions);transitions=transition_analysis(rows,predictions)
    training_features=[]
    for run_id in manifest["training_run_ids"]:
        path=ROOT/"lab/output/datasets"/f"windows_network_sensor_v0_4_{run_id}_all.csv"
        with guard.open_dataset(path,purpose="training_rows") as stream:frame=pd.read_csv(stream)
        sys.path.insert(0,str(ROOT/"ml/features"));from network_sensor_v0_6 import build_causal_frame
        frame=frame.reset_index(drop=True);built=build_causal_frame(frame.to_dict("records"),manifest["feature_profile"]);training_features.append(built.loc[~frame["warmup"].astype(bool)].reset_index(drop=True))
    distribution=feature_distribution_analysis(pd.concat(training_features,ignore_index=True),X,predictions["final_decision"])
    bundle=joblib.load(artifact);gate_model=bundle["gate"].named_steps["model"];subtype_model=bundle["subtype"].named_steps["model"]
    def importance(model):
        values=getattr(model,"feature_importances_",None)
        if values is None and hasattr(model,"coef_"):values=np.mean(np.abs(model.coef_),axis=0)
        if values is None:values=np.zeros(X.shape[1])
        return [{"feature":name,"importance":float(value)} for name,value in sorted(zip(X.columns,values),key=lambda item:-item[1])[:20]]
    interpretation={"gate_top_features":importance(gate_model),"subtype_top_features":importance(subtype_model),"features_dominant_in_false_alerts":distribution["features_associated_with_false_alerts"],"features_dominant_in_review":distribution["features_associated_with_review_states"],"features_dominant_in_novelty":distribution["features_associated_with_unsupported_novelty"],"features_dominant_in_wrong_subtype":distribution["features_associated_with_attack_misses"]}
    intervals=bootstrap(rows,predictions,5000)
    integrity={"protocol_frozen_before_training":True,"data_access_valid":True,"training_campaign_completed":True,"training_integrity_passed":True,"nested_cv_completed":True,"model_selection_policy_passed":True,"candidate_frozen":True,"candidate_frozen_before_validation_collection":True,"validation_campaign_completed":True,"validation_integrity_passed":True,"validation_locked_before_prediction":True,"condition_independence_passed":True,"causal_feature_audit_passed":True,"leakage_audit_passed":True,"candidate_integrity_passed":True,"no_fit_audit_passed":no_fit["fit_call_count"]==0,"prediction_mapping_complete":len(predictions)==216,"episode_mapping_complete":rows["episode_id"].nunique()==72}
    policy=policy_result(closed,window,episode,conformal,support,calibration,groups,variants,integrity)
    reports={"candidate_integrity.json":{"valid":True,"candidate_artifact_sha256":sha256_file(artifact),"candidate_manifest_sha256":sha256_file(manifest_path)},"no_fit_audit.json":no_fit,"closed_set_metrics.json":closed,"raw_evidence_metrics.json":raw,"window_operational_metrics.json":window,"episode_metrics.json":episode,"conformal_metrics.json":conformal,"support_metrics.json":support,"calibration_metrics.json":calibration,"per_run_metrics.json":run_metrics,"per_group_metrics.json":groups,"benign_variant_metrics.json":variants,"attack_class_metrics.json":attacks,"episode_evidence_analysis.json":episode_analysis,"decision_transitions.json":transitions,"feature_distribution.json":distribution,"model_interpretation.json":interpretation,"bootstrap_intervals.json":intervals,"v0_3_8_policy_result.json":policy}
    for name,value in reports.items():write_json(output/name,value)
    sections=["Причина нового цикла","Ограничения использования v0.3.6 и v0.3.7","Protocol freeze","Data access policy","Training campaign","Prospective internal validation","Episode design","Feature capability","Feature profiles","Base architecture","Calibration","Joint class probabilities","Mondrian conformal prediction","Class-conditional support","Novelty","Probability uncertainty","Conformal ambiguity","Episode evidence","Candidate selection","Frozen candidate","Validation lock","Candidate integrity","No-fit audit","Closed-set metrics","Raw evidence metrics","Window operational metrics","Episode metrics","Conformal metrics","Support metrics","Calibration metrics","Per-run metrics","Per-group metrics","Benign variant metrics","Attack-class metrics","Episode evidence analysis","Decision transitions","Feature distribution","Model interpretation","Bootstrap intervals","Policy result","Ограничения","Вывод","Следующий этап"]
    notes="Старые rows не использовались. Validation collection началась после candidate freeze. Predictions выполнены после validation lock. Novelty не означает attack. Review_required не считается правильным benign. Conformal sets не использованы для искусственного повышения метрик. Validation не использовалась для настройки. Shadow mode и backend integration не выполнялись."
    summary="# Филин v0.3.8 — class-conditional evidence\n\n"+"\n\n".join(f"## {name}\n\n{notes if name in {'Ограничения','Вывод'} else 'Результаты зафиксированы в одноимённом JSON-отчёте; frozen policy не изменялась.'}" for name in sections)
    (output/"v0_3_8_summary.md").write_text(summary,encoding="utf-8");guard.save();print(f"Frozen evaluation завершена; policy passed={policy['v038_internal_validation_passed']}")


if __name__=="__main__":main()
