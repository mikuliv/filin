"""Nested grouped model selection и freeze единственного кандидата v0.3.7."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, log_loss
from sklearn.model_selection import StratifiedGroupKFold
import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from data_access_guard import DataAccessGuard
from pipeline import (
    ATTACK_CLASSES,
    DECISION_STATES,
    PROFILES,
    BenignOODGuard,
    GroupAwareSigmoidCalibrator,
    aligned_probabilities,
    build_feature_sets,
    calibrate_aligned,
    candidate_passes,
    decide_rows,
    episode_metrics,
    estimator_feature_importance,
    expected_calibration_error,
    make_gate,
    make_subtype,
    model_parameters,
    positive_probability,
    schema_sha,
    scored_features,
    scored_rows,
    select_parameters,
    sha256_file,
    sha256_json,
    window_metrics,
    write_json,
)


GATES = ["logistic_regression", "random_forest", "hist_gradient_boosting"]
SUBTYPES = ["random_forest", "hist_gradient_boosting"]
HIERARCHICAL_PROFILES = ["network_sensor_v0_5_temporal", "network_sensor_v0_5_contextual"]


def load_training(campaign_path: Path, policy_path: Path, report_dir: Path) -> tuple[pd.DataFrame, dict, DataAccessGuard]:
    campaign = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
    guard = DataAccessGuard(ROOT, policy_path, report_dir / "data_access_audit.json")
    frames = []
    for run in campaign["runs"]:
        path = ROOT / "lab" / "output" / "datasets" / f"windows_network_sensor_v0_4_{run['run_id']}_all.csv"
        with guard.open_dataset(path) as stream:
            frame = pd.read_csv(stream)
        frame["environment_group"] = run["group"]
        frame["random_seed"] = run["random_seed"]
        frames.append(frame)
    rows = pd.concat(frames, ignore_index=True)
    if len(rows) != 408 or int((~rows["warmup"].astype(bool)).sum()) != 336:
        raise ValueError(f"Training integrity нарушена: all={len(rows)}, scored={(~rows['warmup'].astype(bool)).sum()}")
    return rows, campaign, guard


def _inner_predictions(X, rows, train_index, gate_name, subtype_name):
    selected_rows = rows.iloc[train_index].reset_index(drop=True)
    selected_X = X.iloc[train_index].reset_index(drop=True)
    groups = selected_rows["run_id"].astype(str).to_numpy()
    labels = selected_rows["label"].astype(str).to_numpy()
    binary = (labels != "benign").astype(int)
    splitter = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42)
    gate_probability = np.zeros(len(selected_rows))
    subtype_probability = np.zeros((len(selected_rows), len(ATTACK_CLASSES)))
    ood_score = np.zeros(len(selected_rows))
    fold_mapping = np.zeros(len(selected_rows), dtype=int)
    for fold, (fit_index, test_index) in enumerate(splitter.split(selected_X, binary, groups), 1):
        gate = make_gate(gate_name).fit(selected_X.iloc[fit_index], binary[fit_index])
        attack_fit = fit_index[binary[fit_index] == 1]
        subtype = make_subtype(subtype_name).fit(selected_X.iloc[attack_fit], labels[attack_fit])
        ood = IsolationForest(n_estimators=300, max_samples="auto", contamination="auto",
                              random_state=42, n_jobs=-1).fit(selected_X.iloc[fit_index[binary[fit_index] == 0]])
        gate_probability[test_index] = positive_probability(gate, selected_X.iloc[test_index])
        subtype_probability[test_index] = aligned_probabilities(subtype, selected_X.iloc[test_index])
        ood_score[test_index] = -ood.score_samples(selected_X.iloc[test_index])
        fold_mapping[test_index] = fold
    return selected_rows, gate_probability, subtype_probability, ood_score, fold_mapping


def _depth_score(rows, gate_probability, subtype_probability):
    labels = rows["label"].astype(str).to_numpy()
    binary = labels != "benign"
    gate = balanced_accuracy_score(binary, gate_probability >= .5)
    subtype = balanced_accuracy_score(labels[binary], np.array(ATTACK_CLASSES)[np.argmax(subtype_probability[binary], axis=1)])
    return float(gate + subtype)


def _fold_parameters(parameters):
    return {
        "gate_benign_threshold": parameters.gate_benign_threshold,
        "gate_attack_threshold": parameters.gate_attack_threshold,
        "subtype_confidence_threshold": parameters.subtype_confidence_threshold,
        "ood_threshold": parameters.ood_threshold,
        "temporal_variant": parameters.temporal_variant,
        "temporal_alpha": parameters.temporal_alpha,
        "temporal_activation_threshold": parameters.temporal_activation_threshold,
    }


def evaluate_candidate(rows, feature_sets, profile, gate_name, subtype_name):
    labels = rows["label"].astype(str).to_numpy()
    binary = (labels != "benign").astype(int)
    groups = rows["run_id"].astype(str).to_numpy()
    splitter = StratifiedGroupKFold(n_splits=6, shuffle=True, random_state=42)
    gate_oof = np.zeros(len(rows))
    subtype_oof = np.zeros((len(rows), len(ATTACK_CLASSES)))
    raw_gate_oof = np.zeros(len(rows))
    raw_subtype_oof = np.zeros((len(rows), len(ATTACK_CLASSES)))
    ood_oof = np.zeros(len(rows))
    state_oof = np.empty(len(rows), dtype=object)
    outer_fold = np.zeros(len(rows), dtype=int)
    fold_records = []
    depth_counter = Counter()
    for fold, (train_index, test_index) in enumerate(splitter.split(np.zeros(len(rows)), binary, groups), 1):
        best_depth = None
        best_inner = None
        for depth in (3, 4, 6):
            X = scored_features(ALL_ROWS, feature_sets, profile, depth)
            inner = _inner_predictions(X, rows, train_index, gate_name, subtype_name)
            score = _depth_score(inner[0], inner[1], inner[2])
            if best_inner is None or score > best_inner[0]:
                best_depth = depth
                best_inner = (score, inner)
        depth_counter[best_depth] += 1
        _, (inner_rows, inner_gate_raw, inner_subtype_raw, inner_ood, inner_fold) = best_inner
        inner_binary = (inner_rows["label"].astype(str).to_numpy() != "benign").astype(int)
        inner_labels = inner_rows["label"].astype(str).to_numpy()
        gate_calibrator = GroupAwareSigmoidCalibrator().fit(inner_gate_raw, inner_binary)
        subtype_calibrator = GroupAwareSigmoidCalibrator().fit(inner_subtype_raw[inner_binary == 1], inner_labels[inner_binary == 1])
        inner_gate = gate_calibrator.predict_proba(inner_gate_raw)[:, list(gate_calibrator.model.classes_).index(1)]
        inner_subtype = calibrate_aligned(subtype_calibrator, inner_subtype_raw)
        parameters, inner_selection = select_parameters(inner_rows, inner_gate, inner_subtype, inner_ood)

        X = scored_features(ALL_ROWS, feature_sets, profile, best_depth)
        gate = make_gate(gate_name).fit(X.iloc[train_index], binary[train_index])
        attack_train = train_index[binary[train_index] == 1]
        subtype = make_subtype(subtype_name).fit(X.iloc[attack_train], labels[attack_train])
        ood = IsolationForest(n_estimators=300, max_samples="auto", contamination="auto",
                              random_state=42, n_jobs=-1).fit(X.iloc[train_index[binary[train_index] == 0]])
        raw_gate = positive_probability(gate, X.iloc[test_index])
        raw_subtype = aligned_probabilities(subtype, X.iloc[test_index])
        calibrated_gate = gate_calibrator.predict_proba(raw_gate)[:, list(gate_calibrator.model.classes_).index(1)]
        calibrated_subtype = calibrate_aligned(subtype_calibrator, raw_subtype)
        ood_score = -ood.score_samples(X.iloc[test_index])
        test_rows = rows.iloc[test_index].reset_index(drop=True)
        decisions = decide_rows(test_rows, calibrated_gate, calibrated_subtype, ood_score, parameters)
        gate_oof[test_index] = calibrated_gate
        subtype_oof[test_index] = calibrated_subtype
        raw_gate_oof[test_index] = raw_gate
        raw_subtype_oof[test_index] = raw_subtype
        ood_oof[test_index] = ood_score
        state_oof[test_index] = decisions["decision_state"].to_numpy()
        outer_fold[test_index] = fold
        fold_records.append({
            "outer_fold": fold,
            "train_run_ids": sorted(set(groups[train_index])),
            "test_run_ids": sorted(set(groups[test_index])),
            "inner_splits": 4,
            "selected_rolling_history_depth": best_depth,
            "selected_parameters": _fold_parameters(parameters),
            "inner_policy_passed": inner_selection["policy_passed"],
        })
    decisions = pd.DataFrame({"decision_state": state_oof, "gate_probability": gate_oof,
                              "ood_score": ood_oof,
                              "subtype_prediction": np.array(ATTACK_CLASSES)[np.argmax(subtype_oof, axis=1)],
                              "subtype_confidence": np.max(subtype_oof, axis=1)})
    metrics = window_metrics(rows, decisions)
    episodes = episode_metrics(rows, decisions)
    passed, checks = candidate_passes(metrics, episodes)
    return {
        "candidate_id": f"hierarchical:{profile}:{gate_name}:{subtype_name}",
        "feature_profile": profile,
        "feature_count": len(PROFILES[profile]),
        "gate_model": gate_name,
        "subtype_model": subtype_name,
        "rolling_history_depth": depth_counter.most_common(1)[0][0],
        "outer_folds": fold_records,
        "metrics": metrics,
        "episode_metrics": episodes,
        "policy_passed": passed,
        "policy_checks": checks,
        "oof": {
            "raw_gate": raw_gate_oof, "raw_subtype": raw_subtype_oof,
            "gate": gate_oof, "subtype": subtype_oof, "ood": ood_oof,
            "states": state_oof, "outer_fold": outer_fold,
        },
    }


def ranking(record):
    metrics = record["metrics"]
    complexity = {"logistic_regression": 0, "random_forest": 1, "hist_gradient_boosting": 2}
    return (
        int(record["policy_passed"]), -metrics["false_positive_rate"], metrics["benign_recall"],
        metrics["attack_alert_recall"], metrics["operational_macro_f1"],
        -record.get("gate_ece", 1.0), -record.get("run_f1_std", 1.0),
        -record["feature_count"], -complexity[record["gate_model"]] - complexity[record["subtype_model"]],
    )


def fit_frozen(selected, rows, feature_sets, report_dir, artifact_dir, campaign, args):
    profile = selected["feature_profile"]
    depth = selected["rolling_history_depth"]
    X = scored_features(ALL_ROWS, feature_sets, profile, depth)
    labels = rows["label"].astype(str).to_numpy()
    binary = (labels != "benign").astype(int)
    groups = rows["run_id"].astype(str).to_numpy()
    raw_gate = np.zeros(len(rows))
    raw_subtype = np.zeros((len(rows), len(ATTACK_CLASSES)))
    ood_oof = np.zeros(len(rows))
    folds = np.zeros(len(rows), dtype=int)
    splitter = StratifiedGroupKFold(n_splits=6, shuffle=True, random_state=42)
    for fold, (train_index, test_index) in enumerate(splitter.split(X, binary, groups), 1):
        gate = make_gate(selected["gate_model"]).fit(X.iloc[train_index], binary[train_index])
        attack_train = train_index[binary[train_index] == 1]
        subtype = make_subtype(selected["subtype_model"]).fit(X.iloc[attack_train], labels[attack_train])
        ood = IsolationForest(n_estimators=300, max_samples="auto", contamination="auto", random_state=42, n_jobs=-1)
        ood.fit(X.iloc[train_index[binary[train_index] == 0]])
        raw_gate[test_index] = positive_probability(gate, X.iloc[test_index])
        raw_subtype[test_index] = aligned_probabilities(subtype, X.iloc[test_index])
        ood_oof[test_index] = -ood.score_samples(X.iloc[test_index])
        folds[test_index] = fold
    gate_calibrator = GroupAwareSigmoidCalibrator().fit(raw_gate, binary)
    subtype_calibrator = GroupAwareSigmoidCalibrator().fit(raw_subtype[binary == 1], labels[binary == 1])
    calibrated_gate = gate_calibrator.predict_proba(raw_gate)[:, list(gate_calibrator.model.classes_).index(1)]
    calibrated_subtype = calibrate_aligned(subtype_calibrator, raw_subtype)
    parameters, parameter_selection = select_parameters(rows, calibrated_gate, calibrated_subtype, ood_oof)
    final_decisions = decide_rows(rows, calibrated_gate, calibrated_subtype, ood_oof, parameters)
    final_metrics = window_metrics(rows, final_decisions)
    final_episodes = episode_metrics(rows, final_decisions)
    policy_passed, checks = candidate_passes(final_metrics, final_episodes)
    def component(gate_probability,subtype_probability,ood_score,decision_parameters):
        decisions=decide_rows(rows,gate_probability,subtype_probability,ood_score,decision_parameters)
        return {'window_metrics':window_metrics(rows,decisions),'episode_metrics':episode_metrics(rows,decisions)}
    no_ood=float(np.max(ood_oof)+1.0)
    raw_parameters=type(parameters)(parameters.gate_benign_threshold,parameters.gate_attack_threshold,
        parameters.subtype_confidence_threshold,no_ood,'none',parameters.temporal_alpha,parameters.temporal_activation_threshold)
    calibrated_parameters=type(parameters)(parameters.gate_benign_threshold,parameters.gate_attack_threshold,
        parameters.subtype_confidence_threshold,no_ood,'none',parameters.temporal_alpha,parameters.temporal_activation_threshold)
    ood_parameters=type(parameters)(parameters.gate_benign_threshold,parameters.gate_attack_threshold,
        parameters.subtype_confidence_threshold,parameters.ood_threshold,'none',parameters.temporal_alpha,parameters.temporal_activation_threshold)
    component_ablation={'hierarchical_contextual':component(raw_gate,raw_subtype,np.zeros(len(rows)),raw_parameters),
        'hierarchical_contextual_calibration':component(calibrated_gate,calibrated_subtype,np.zeros(len(rows)),calibrated_parameters),
        'hierarchical_contextual_calibration_ood':component(calibrated_gate,calibrated_subtype,ood_oof,ood_parameters),
        'hierarchical_contextual_calibration_ood_temporal':component(calibrated_gate,calibrated_subtype,ood_oof,parameters)}

    gate = make_gate(selected["gate_model"]).fit(X, binary)
    subtype = make_subtype(selected["subtype_model"]).fit(X.loc[binary == 1], labels[binary == 1])
    ood_guard = BenignOODGuard(.975).fit(X.loc[binary == 0])
    ood_guard.threshold = parameters.ood_threshold
    artifact = {
        "architecture_id": "network_sensor_v0_5_hierarchical",
        "feature_profile": profile,
        "rolling_history_depth": depth,
        "gate": gate,
        "subtype": subtype,
        "gate_calibrator": gate_calibrator,
        "subtype_calibrator": subtype_calibrator,
        "ood_guard": ood_guard,
        "decision_parameters": _fold_parameters(parameters),
        "classes": ATTACK_CLASSES,
        "ordered_feature_list": PROFILES[profile],
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "network_sensor_v0_5_hierarchical.joblib"
    joblib.dump(artifact, artifact_path)
    artifact_hash = sha256_file(artifact_path)
    oof_table = rows[["run_id", "execution_id", "episode_id", "label", "variant_id"]].copy()
    oof_table["outer_fold"] = folds
    oof_table["raw_gate_probability"] = raw_gate
    oof_table["calibrated_gate_probability"] = calibrated_gate
    oof_table["ood_score"] = ood_oof
    oof_table["decision_state"] = final_decisions["decision_state"]
    for index, name in enumerate(ATTACK_CLASSES):
        oof_table[f"raw_subtype_{name}"] = raw_subtype[:, index]
        oof_table[f"calibrated_subtype_{name}"] = calibrated_subtype[:, index]
    oof_payload = oof_table.to_dict("records")
    write_json(report_dir / "nested_cv_oof_predictions.json", oof_payload)
    training_hashes = {access["path"]: access["sha256"] for access in GUARD.accesses}
    policy_path = Path(args.model_selection_policy)
    data_policy_path = Path(args.data_policy)
    feature_builder_path = ROOT / "ml" / "features" / "network_sensor_v0_5.py"
    manifest = {
        "candidate_id": selected["candidate_id"],
        "architecture_id": "network_sensor_v0_5_hierarchical",
        "binary_gate_model": selected["gate_model"],
        "binary_gate_parameters": model_parameters(selected["gate_model"], "gate"),
        "subtype_model": selected["subtype_model"],
        "subtype_parameters": model_parameters(selected["subtype_model"], "subtype"),
        "feature_profile": profile,
        "feature_count": len(PROFILES[profile]),
        "ordered_feature_list": PROFILES[profile],
        "feature_schema_sha256": schema_sha(profile),
        "feature_builder_sha256": sha256_file(feature_builder_path),
        "rolling_history_depth": depth,
        "calibration_method": "group_aware_oof_sigmoid",
        "calibrator_parameters": {"binary_gate": gate_calibrator.parameters(), "attack_subtype": subtype_calibrator.parameters()},
        "calibration_training_run_ids": sorted(set(rows["run_id"])),
        "calibration_oof_hash": sha256_json(oof_payload),
        "calibration_fitted_on_validation": False,
        "ood_model": "IsolationForest",
        "ood_parameters": {"n_estimators": 300, "max_samples": "auto", "contamination": "auto", "random_state": 42, "n_jobs": -1},
        "ood_threshold": parameters.ood_threshold,
        "ood_quantile_grid": [0.95, 0.975, 0.99],
        "gate_benign_threshold": parameters.gate_benign_threshold,
        "gate_attack_threshold": parameters.gate_attack_threshold,
        "subtype_confidence_threshold": parameters.subtype_confidence_threshold,
        "temporal_evidence_variant": parameters.temporal_variant,
        "temporal_evidence_parameters": {"alpha": parameters.temporal_alpha, "activation_threshold": parameters.temporal_activation_threshold},
        "classes": ["benign"] + ATTACK_CLASSES,
        "decision_states": DECISION_STATES,
        "training_run_ids": sorted(set(rows["run_id"])),
        "training_dataset_sha256": sha256_json(training_hashes),
        "training_execution_mapping_sha256": sha256_json(rows[["run_id", "execution_id", "episode_id", "label"]].to_dict("records")),
        "nested_cv_policy_sha256": sha256_file(policy_path),
        "model_selection_policy_sha256": sha256_file(policy_path),
        "data_access_policy_sha256": sha256_file(data_policy_path),
        "validation_campaign_sha256": sha256_file(ROOT / "lab/campaigns/v0_3_7_internal_validation.yaml"),
        "validation_policy_sha256": sha256_file(ROOT / "ml/experiments/v0_3_7/internal_validation_policy.yaml"),
        "artifact_paths": [artifact_path.relative_to(ROOT).as_posix()],
        "artifact_sha256": {artifact_path.relative_to(ROOT).as_posix(): artifact_hash},
        "candidate_frozen_at": datetime.now(timezone.utc).isoformat(),
        "candidate_frozen_before_validation": True,
        "model_trained_on_v036_data": False,
        "prohibit_refit_on_validation": True,
        "prohibit_refit_on_v036": True,
    }
    manifest_path = ROOT / "ml" / "experiments" / "v0_3_7" / "frozen_candidate_manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    manifest_hash = sha256_file(manifest_path)
    calibration = {
        "method": "group_aware_oof_sigmoid", "training_run_ids": sorted(set(groups)),
        "oof_hash": sha256_json(oof_payload), "fitted_on_validation": False,
        "binary_gate": {
            "before": {"log_loss": log_loss(binary, raw_gate), "brier": brier_score_loss(binary, raw_gate), "ece": expected_calibration_error(binary, raw_gate)},
            "after": {"log_loss": log_loss(binary, calibrated_gate), "brier": brier_score_loss(binary, calibrated_gate), "ece": expected_calibration_error(binary, calibrated_gate)},
            "parameters": gate_calibrator.parameters(),
        },
        "subtype": {"parameters": subtype_calibrator.parameters(), "ece": expected_calibration_error(
            np.array([ATTACK_CLASSES.index(value) for value in labels[binary == 1]]), calibrated_subtype[binary == 1])},
    }
    write_json(report_dir / "calibration_analysis.json", calibration)
    write_json(report_dir / "ood_selection.json", {"model": "IsolationForest", "quantile_grid": [.95, .975, .99],
                                                     "selected_threshold": parameters.ood_threshold, "fitted_on_validation": False})
    write_json(report_dir / "abstention_selection.json", {"selected": _fold_parameters(parameters), "training_oof_only": True,
                                                            "metrics": final_metrics, "policy_checks": checks})
    write_json(report_dir / "temporal_evidence_selection.json", {"selected_variant": parameters.temporal_variant,
                                                                   "parameters": _fold_parameters(parameters), "training_oof_only": True})
    write_json(report_dir / "candidate_freeze_audit.json", {"candidate_frozen": True, "candidate_frozen_before_validation": True,
                                                             "artifact_sha256": artifact_hash, "manifest_sha256": manifest_hash,
                                                             "prohibit_refit_on_validation": True})
    return manifest, manifest_hash, artifact, final_metrics, final_episodes, policy_passed, component_ablation


def control_ablation(rows, feature_sets):
    X = scored_features(ALL_ROWS, feature_sets, "network_sensor_v0_4_rates_control", 0)
    labels = rows["label"].astype(str).to_numpy()
    groups = rows["run_id"].astype(str).to_numpy()
    predictions = np.empty(len(rows), dtype=object)
    splitter = StratifiedGroupKFold(n_splits=6, shuffle=True, random_state=42)
    for train, test in splitter.split(X, labels, groups):
        model = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2,
                                       class_weight="balanced_subsample", random_state=42, n_jobs=-1).fit(X.iloc[train], labels[train])
        predictions[test] = model.predict(X.iloc[test])
    return {"profile": "network_sensor_v0_4_rates_control", "feature_count": 16,
            "closed_set_macro_f1": float(__import__("sklearn.metrics").metrics.f1_score(labels, predictions, average="macro")),
            "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
            "benign_recall": float(np.mean(predictions[labels == "benign"] == "benign")),
            "false_positive_rate": float(np.mean(predictions[labels == "benign"] != "benign"))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-campaign", default="lab/campaigns/v0_3_7_training.yaml")
    parser.add_argument("--data-policy", default="ml/experiments/v0_3_7/data_access_policy.yaml")
    parser.add_argument("--model-selection-policy", default="ml/experiments/v0_3_7/model_selection_policy.yaml")
    parser.add_argument("--report-dir", default="ml/reports/v0_3_7")
    parser.add_argument("--artifact-dir", default="ml/artifacts/v0_3_7")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    report_dir = ROOT / args.report_dir
    artifact_dir = ROOT / args.artifact_dir
    manifest_path = ROOT / "ml/experiments/v0_3_7/frozen_candidate_manifest.yaml"
    results_path = report_dir / "nested_cv_results.json"
    if args.resume and manifest_path.exists() and results_path.exists():
        print(json.dumps({"status": "resumed", "candidate_manifest": str(manifest_path)}, ensure_ascii=False))
        return
    global ALL_ROWS, GUARD
    ALL_ROWS, campaign, GUARD = load_training(ROOT / args.training_campaign, ROOT / args.data_policy, report_dir)
    rows = scored_rows(ALL_ROWS)
    feature_sets = build_feature_sets(ALL_ROWS)
    write_json(report_dir / "feature_profiles.json", {name: {"feature_count": len(values), "ordered_features": values,
                                                               "schema_sha256": schema_sha(name)} for name, values in PROFILES.items()})
    records = []
    for profile in HIERARCHICAL_PROFILES:
        for gate in GATES:
            for subtype in SUBTYPES:
                print(f"nested CV: {profile} / {gate} / {subtype}", flush=True)
                records.append(evaluate_candidate(rows, feature_sets, profile, gate, subtype))
    selected = max(records, key=ranking)
    serializable = []
    for record in records:
        item = {key: value for key, value in record.items() if key != "oof"}
        serializable.append(item)
    write_json(results_path, {"design": {"outer": "StratifiedGroupKFold(6, shuffle=True, random_state=42)",
                                          "inner": "StratifiedGroupKFold(4, shuffle=True, random_state=42)", "group": "run_id"},
                              "base_combinations": serializable, "completed": True})
    manifest, manifest_hash, artifact, final_metrics, final_episodes, passed, component_ablation = fit_frozen(
        selected, rows, feature_sets, report_dir, artifact_dir, campaign, args)
    ablation = {
        "control_rates16_flat": control_ablation(rows, feature_sets),
        "hierarchical_temporal": next(item for item in serializable if item["feature_profile"].endswith("temporal")),
        **component_ablation,
        "validation_used": False,
    }
    write_json(report_dir / "ablation_metrics.json", ablation)
    write_json(report_dir / "candidate_selection.json", {"selected_candidate_id": manifest["candidate_id"],
                                                           "selection_policy_passed": passed,
                                                           "ranking": [item["candidate_id"] for item in sorted(serializable, key=ranking, reverse=True)],
                                                           "candidate_manifest_sha256": manifest_hash})
    print(json.dumps({"status": "completed", "candidate_id": manifest["candidate_id"],
                      "nested_cv_policy_passed": passed, "manifest_sha256": manifest_hash}, ensure_ascii=False, indent=2))


ALL_ROWS = None
GUARD = None
if __name__ == "__main__":
    main()
