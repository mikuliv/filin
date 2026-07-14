"""Nested grouped selection и freeze единственного evidence candidate v0.3.8."""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(ROOT / "ml/features"), str(ROOT / "ml/models")]

from data_access_guard import DataAccessGuard
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
from mondrian_conformal_classifier import MondrianConformalClassifier
from class_conditional_support import ClassConditionalSupport
from pipeline import (ATTACK_CLASSES, CLASSES, GATES, PROFILES, SUBTYPES, base_gate_flags,
    build_feature_frame, calibrated_joint, closed_set_metrics, conformal_metrics, evidence_decisions,
    make_gate, make_subtype, model_parameters, oof_base, operational_metrics, ordered_features,
    schema_sha256, sha256_file, sha256_json, support_metrics, write_json)


def load_training(campaign: dict, output_root: Path, guard: DataAccessGuard) -> pd.DataFrame:
    frames = []
    for run in campaign["runs"]:
        path = output_root / "datasets" / f"windows_network_sensor_v0_4_{run['run_id']}_all.csv"
        with guard.open_dataset(path, purpose="training_rows") as stream:
            frame = pd.read_csv(stream)
        frame["environment_group"] = run["group"]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def candidate_rank(result: dict):
    metrics = result["closed_set_metrics"]
    complexity = (len(ordered_features(result["feature_profile"])), GATES.index(result["gate_model"]), SUBTYPES.index(result["subtype_model"]))
    return (metrics["FPR"], -metrics["benign_recall"], -metrics["attack_macro_recall"], -metrics["macro_f1"], metrics["ECE"], *complexity)


def main():
    parser = argparse.ArgumentParser(description="Выполнить nested grouped selection v0.3.8")
    parser.add_argument("--training-campaign", required=True)
    parser.add_argument("--data-policy", required=True)
    parser.add_argument("--model-selection-policy", required=True)
    parser.add_argument("--output-root", required=True, default="lab/output")
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    report_dir, artifact_dir = ROOT / args.report_dir, ROOT / args.artifact_dir
    result_path = report_dir / "nested_cv_results.json"
    manifest_path = HERE / "frozen_candidate_manifest.yaml"
    if args.resume and result_path.exists() and manifest_path.exists():
        print("Nested CV и candidate freeze уже завершены; повтор не выполняется.")
        return
    report_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    campaign = yaml.safe_load((ROOT / args.training_campaign).read_text(encoding="utf-8"))
    guard = DataAccessGuard(ROOT, ROOT / args.data_policy, report_dir / "data_access_audit.json")
    all_rows = load_training(campaign, ROOT / args.output_root, guard)
    profile_data = {profile: build_feature_frame(all_rows, profile) for profile in PROFILES}
    base_results, oof_cache = [], {}
    for profile, gate_name, subtype_name in itertools.product(PROFILES, GATES, SUBTYPES):
        rows, X = profile_data[profile]
        oof = oof_base(rows, X, gate_name, subtype_name)
        candidate_id = f"base:{profile}:{gate_name}:{subtype_name}"
        flags = base_gate_flags(oof["metrics"])
        record = {"candidate_id": candidate_id, "feature_profile": profile, "feature_count": X.shape[1],
            "gate_model": gate_name, "subtype_model": subtype_name, "closed_set_metrics": oof["metrics"],
            "base_gate_flags": flags, "base_gates_passed": all(flags.values()), "outer_fold_audit": oof["fold_audit"]}
        base_results.append(record)
        oof_cache[candidate_id] = oof
    ranked = sorted(base_results, key=candidate_rank)
    eligible = [value for value in ranked if value["base_gates_passed"]]
    finalists = (eligible or ranked)[:3]
    evidence_results = []
    rows_by_profile = {name: value[0] for name, value in profile_data.items()}
    for finalist in finalists:
        rows, X = profile_data[finalist["feature_profile"]]
        labels = rows["episode_class"].astype(str).to_numpy()
        binary = (labels != "benign").astype(int)
        oof = oof_cache[finalist["candidate_id"]]
        gate_calibrator = GroupAwareSigmoidCalibrator().fit(oof["gate_oof"], binary)
        subtype_calibrator = GroupAwareSigmoidCalibrator().fit(oof["subtype_oof"][binary == 1], labels[binary == 1])
        calibrated = calibrated_joint(gate_calibrator, subtype_calibrator, oof["gate_oof"], oof["subtype_oof"])
        for alpha, k_neighbors, quantile in itertools.product((.05, .10), (3, 5), (.95, .975)):
            conformal = MondrianConformalClassifier(alpha).fit(calibrated, labels, CLASSES, source="training_oof")
            support = ClassConditionalSupport(k_neighbors, quantile).fit(X, labels, source="training")
            for parameters in (
                {"policy": "consistent_2_of_3", "decay": .7, "activation_threshold": 1.6, "benign_reset_probability": .8},
                {"policy": "signed_decay", "decay": .5, "activation_threshold": 1.2, "benign_reset_probability": .7},
                {"policy": "signed_decay", "decay": .7, "activation_threshold": 1.6, "benign_reset_probability": .8},
                {"policy": "hybrid", "decay": .5, "activation_threshold": 1.2, "benign_reset_probability": .7},
                {"policy": "hybrid", "decay": .7, "activation_threshold": 1.6, "benign_reset_probability": .8},
            ):
                decisions = evidence_decisions(rows, calibrated, conformal, support, X, parameters)
                window, episode = operational_metrics(rows, decisions)
                cmetrics = conformal_metrics(labels, conformal.predict_set(calibrated))
                smetrics = support_metrics(labels, support.support_sets(X))
                identifier = f"{finalist['candidate_id']}:a{alpha}:k{k_neighbors}:q{quantile}:{parameters['policy']}:{parameters['decay']}:{parameters['activation_threshold']}:{parameters['benign_reset_probability']}"
                evidence_results.append({"candidate_id": identifier, "base_candidate_id": finalist["candidate_id"],
                    "feature_profile": finalist["feature_profile"], "gate_model": finalist["gate_model"], "subtype_model": finalist["subtype_model"],
                    "conformal_alpha": alpha, "support_k": k_neighbors, "support_quantile": quantile,
                    "episode_parameters": parameters, "window_metrics": window, "episode_metrics": episode,
                    "conformal_metrics": cmetrics, "support_metrics": smetrics})
    evidence_results.sort(key=lambda value: (value["episode_metrics"]["benign_episode_false_alert_rate"],
        -value["episode_metrics"]["episode_alert_precision"], -value["episode_metrics"]["attack_episode_recall"],
        value["episode_metrics"]["benign_episode_high_severity_alert_rate"], value["window_metrics"]["review_rate"],
        -value["window_metrics"]["benign_recall"], -value["conformal_metrics"]["empirical_coverage_overall"]))
    selected = evidence_results[0]
    base = next(value for value in finalists if value["candidate_id"] == selected["base_candidate_id"])
    rows, X = profile_data[selected["feature_profile"]]
    labels = rows["episode_class"].astype(str).to_numpy()
    binary = (labels != "benign").astype(int)
    oof = oof_cache[selected["base_candidate_id"]]
    gate_calibrator = GroupAwareSigmoidCalibrator().fit(oof["gate_oof"], binary)
    subtype_calibrator = GroupAwareSigmoidCalibrator().fit(oof["subtype_oof"][binary == 1], labels[binary == 1])
    calibrated = calibrated_joint(gate_calibrator, subtype_calibrator, oof["gate_oof"], oof["subtype_oof"])
    conformal = MondrianConformalClassifier(selected["conformal_alpha"]).fit(calibrated, labels, CLASSES, source="training_oof")
    support = ClassConditionalSupport(selected["support_k"], selected["support_quantile"]).fit(X, labels, source="training")
    gate = make_gate(selected["gate_model"]).fit(X, binary)
    subtype = make_subtype(selected["subtype_model"]).fit(X.loc[binary == 1], labels[binary == 1])
    bundle = {"architecture_id": "network_sensor_v0_6_class_conditional_evidence", "classes": CLASSES,
        "attack_classes": ATTACK_CLASSES, "feature_profile": selected["feature_profile"], "ordered_features": ordered_features(selected["feature_profile"]),
        "gate": gate, "subtype": subtype, "gate_calibrator": gate_calibrator, "subtype_calibrator": subtype_calibrator,
        "conformal": conformal, "support": support, "episode_parameters": selected["episode_parameters"]}
    artifact_path = artifact_dir / "frozen_candidate.joblib"
    joblib.dump(bundle, artifact_path)
    dataset_hash = sha256_json([sha256_file(ROOT / args.output_root / "datasets" / f"windows_network_sensor_v0_4_{run['run_id']}_all.csv") for run in campaign["runs"]])
    mapping_hash = sha256_json(rows[["run_id", "execution_id", "episode_id", "episode_phase", "episode_class"]].to_dict("records"))
    oof_hash = sha256_json({"gate": oof["gate_oof"].tolist(), "subtype": oof["subtype_oof"].tolist(), "labels": labels.tolist()})
    protocol_hash = sha256_file(ROOT / "ml/experiments/v0_3_8/protocol.yaml")
    manifest = {
        "candidate_id": selected["candidate_id"], "architecture_id": "network_sensor_v0_6_class_conditional_evidence",
        "feature_profile": selected["feature_profile"], "feature_count": len(ordered_features(selected["feature_profile"])),
        "ordered_feature_list": ordered_features(selected["feature_profile"]), "feature_schema_sha256": schema_sha256(selected["feature_profile"]),
        "feature_builder_sha256": sha256_file(ROOT / "ml/features/network_sensor_v0_6.py"),
        "binary_gate_model": selected["gate_model"], "binary_gate_parameters": model_parameters(selected["gate_model"]),
        "binary_gate_artifact_sha256": sha256_file(artifact_path), "subtype_model": selected["subtype_model"],
        "subtype_parameters": model_parameters(selected["subtype_model"]), "subtype_artifact_sha256": sha256_file(artifact_path),
        "calibration_method": "group_aware_oof_sigmoid", "gate_calibrator_parameters": gate_calibrator.parameters(),
        "subtype_calibrator_parameters": subtype_calibrator.parameters(), "calibration_oof_sha256": oof_hash,
        "conformal_method": "mondrian_class_conditional", "conformal_alpha": selected["conformal_alpha"],
        "conformal_class_counts": conformal.manifest()["class_calibration_counts"], "conformal_score_hashes": conformal.manifest()["class_score_hashes"],
        "support_method": "robust_scaler_class_conditional_nearest_neighbors", "support_k": selected["support_k"],
        "support_quantile": selected["support_quantile"], "support_class_thresholds": support.thresholds_,
        "support_artifact_sha256": sha256_file(artifact_path), "episode_policy": selected["episode_parameters"]["policy"],
        "episode_parameters": selected["episode_parameters"], "decision_states": ["benign", "review_required:novel", "review_required:ambiguous", "review_required:weak_evidence", "suspicious_unclassified", *[f"attack_candidate:{name}" for name in ATTACK_CLASSES]],
        "classes": CLASSES, "training_run_ids": [run["run_id"] for run in campaign["runs"]],
        "training_dataset_sha256": dataset_hash, "training_mapping_sha256": mapping_hash,
        "data_access_policy_sha256": sha256_file(ROOT / args.data_policy), "model_selection_policy_sha256": sha256_file(ROOT / args.model_selection_policy),
        "protocol_sha256": protocol_hash, "candidate_artifact": artifact_path.relative_to(ROOT).as_posix(),
        "candidate_frozen_at": datetime.now(UTC).isoformat(), "candidate_frozen_before_validation_collection": True,
        "model_trained_on_v036_data": False, "model_trained_on_v037_data": False,
        "prohibit_refit_on_validation": True, "prohibit_tuning_on_validation": True,
    }
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    write_json(report_dir / "nested_cv_results.json", {"nested_cv_completed": True, "outer_splits": 6, "inner_splits": 4, "grouping": "run_id", "base_candidates": base_results})
    write_json(report_dir / "base_finalists.json", {"finalists": finalists, "eligible_finalist_count": len(eligible), "fallback_to_ranked_if_no_gate_pass": not bool(eligible)})
    write_json(report_dir / "calibration_selection.json", {"method": "group_aware_oof_sigmoid", "source": "training_oof", "oof_sha256": oof_hash})
    write_json(report_dir / "conformal_selection.json", {"grid": [.05, .10], "selected": conformal.manifest(), "validation_used": False})
    write_json(report_dir / "support_selection.json", {"k_grid": [3, 5], "quantile_grid": [.95, .975], "selected_k": selected["support_k"], "selected_quantile": selected["support_quantile"], "thresholds": support.thresholds_, "validation_used": False})
    write_json(report_dir / "episode_policy_selection.json", {"training_oof_combinations": len(evidence_results), "selected": selected["episode_parameters"], "validation_used": False})
    write_json(report_dir / "candidate_selection.json", {"selected_candidate": selected, "base_candidate": base, "candidate_count": 12, "evidence_policy_combinations": evidence_results})
    write_json(report_dir / "candidate_freeze_audit.json", {"candidate_frozen": True, "candidate_frozen_before_validation_collection": True, "candidate_artifact_sha256": sha256_file(artifact_path), "candidate_manifest_sha256": sha256_file(manifest_path)})
    write_json(report_dir / "feature_profiles.json", {name: {"feature_count": len(ordered_features(name)), "ordered_features": ordered_features(name), "schema_sha256": schema_sha256(name)} for name in PROFILES})
    guard.save()
    print(f"Выбран и frozen candidate: {selected['candidate_id']}")


if __name__ == "__main__":
    main()
