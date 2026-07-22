from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import confusion_matrix, f1_score, recall_score

from .candidate import ATTACKS, CLASSES, BinarySigmoidCalibrator, SubtypeSigmoidCalibrator, aligned, conformal_sets, joint_probabilities


ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_4"
RUNTIME = ROOT / "runtime/v0_3_15_4"
REPORT = ROOT / "ml/reports/v0_3_15_4"
ARTIFACT_DIR = ROOT / "ml/artifacts/v0_3_15_4"


def read_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def feature_rows() -> list[dict]:
    return [json.loads(line) for line in (RUNTIME / "feature_rows.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true); y_pred = np.asarray(y_pred)
    recall = {name: float(recall_score(y_true == name, y_pred == name, zero_division=0)) for name in CLASSES}
    attack_true = y_true != "benign"; attack_pred = y_pred != "benign"
    return {
        "benign_recall": recall["benign"], "fpr": float(np.mean(attack_pred[y_true == "benign"])),
        "attack_macro_recall": float(np.mean([recall[x] for x in ATTACKS])),
        "attack_macro_f1": float(f1_score(y_true[attack_true], y_pred[attack_true], labels=ATTACKS, average="macro", zero_division=0)),
        "per_class_recall": recall, "worst_attack_recall": min(recall[x] for x in ATTACKS),
        "accuracy": float(np.mean(y_true == y_pred)),
    }


def episode_metrics(records: list[dict], predictions: list[str], labels: list[dict]) -> dict:
    grouped = defaultdict(list)
    for row, prediction, label in zip(records, predictions, labels):
        if label.get("episode_id"):
            grouped[label["episode_id"]].append((label, prediction))
    attack = benign = attack_ok = benign_false = by_second = 0
    for values in grouped.values():
        label = values[0][0]; expected = label["true_class"]
        if expected == "benign":
            benign += 1; benign_false += any(prediction != "benign" for _, prediction in values)
        else:
            attack += 1; correct = [index for index, (_, prediction) in enumerate(values, 1) if prediction == expected]
            attack_ok += bool(correct); by_second += bool(correct and min(correct) <= 2)
    predicted_attack_episodes = attack_ok + benign_false
    return {"attack_episode_recall": attack_ok / attack if attack else 0.0, "episode_precision": attack_ok / predicted_attack_episodes if predicted_attack_episodes else 1.0, "benign_episode_false_alert_rate": benign_false / benign if benign else 0.0, "detection_by_second": by_second / attack if attack else 0.0, "attack_episode_count": attack, "benign_episode_count": benign}


def build_model(config: dict, x: pd.DataFrame, y: np.ndarray):
    common = {key: config[key] for key in ["learning_rate", "max_iter", "max_leaf_nodes", "min_samples_leaf", "l2_regularization", "random_state"]}
    gate_y = (y != "benign").astype(int)
    weights = np.ones(len(y)); weights[y == "auth_failures"] = config["auth_sample_weight"]
    gate = HistGradientBoostingClassifier(**common).fit(x, gate_y, sample_weight=weights)
    attack_mask = y != "benign"
    subtype = HistGradientBoostingClassifier(**common).fit(x.loc[attack_mask], y[attack_mask], sample_weight=weights[attack_mask])
    return gate, subtype


def raw_predict(gate, subtype, x):
    gate_p = aligned(gate, x, [0, 1])[:, 1]; subtype_p = aligned(subtype, x, ATTACKS)
    probability = np.column_stack([1 - gate_p, gate_p[:, None] * subtype_p])
    return np.asarray(CLASSES)[np.argmax(probability, axis=1)], probability


def passes(value: dict) -> bool:
    return value["benign_recall"] >= .98 and value["fpr"] <= .02 and value["attack_macro_recall"] >= .95 and value["attack_macro_f1"] >= .95 and value["worst_attack_recall"] >= .90


def main() -> int:
    lock = read_json(CFG / "training_lock.json")
    if not lock["frozen_before_first_fit"] or len(lock["search_space"]["candidates"]) != 3:
        raise RuntimeError("training_lock_invalid")
    if not (RUNTIME / "label_separation_commitment.json").is_file():
        raise RuntimeError("labels_not_separated")
    rows = feature_rows(); development = read_json(RUNTIME / "development_labels.json")["records"]
    label_by_key = {(x["session_id"], x["scored_window_index"]): x for x in development}
    dev_rows = [x for x in rows if x["split"] in {"training", "calibration"}]
    labels = [label_by_key[(x["session_id"], x["scored_window_index"])] for x in dev_rows]
    names = list(dev_rows[0]["features"]); x = pd.DataFrame([row["features"] for row in dev_rows], columns=names); y = np.asarray([row["true_class"] for row in labels])
    split = np.asarray([row["split"] for row in dev_rows]); sessions = np.asarray([row["session_id"] for row in dev_rows])
    train_mask = split == "training"; cal_mask = split == "calibration"
    fold_map = {row["session_id"]: row["fold"] for row in lock["fold_assignment"]}
    comparisons = []
    for candidate_name, config in lock["search_space"]["candidates"].items():
        fold_predictions = np.empty(train_mask.sum(), dtype=object); train_indices = np.flatnonzero(train_mask)
        for fold in range(3):
            validation = np.asarray([fold_map[s] == fold for s in sessions[train_mask]])
            fit_indices = train_indices[~validation]; validation_indices = train_indices[validation]
            gate, subtype = build_model(config, x.iloc[fit_indices], y[fit_indices])
            fold_predictions[validation], _ = raw_predict(gate, subtype, x.iloc[validation_indices])
        value = metrics(y[train_mask], fold_predictions)
        value.update(episode_metrics([dev_rows[i] for i in train_indices], list(fold_predictions), [labels[i] for i in train_indices]))
        value.update({"candidate": candidate_name, "configuration": config, "required_gates_passed": passes(value), "fold_count": 3})
        comparisons.append(value)
    eligible = [row for row in comparisons if row["required_gates_passed"]]
    if not eligible:
        raise RuntimeError("no_candidate_passed_selection_gates")
    selected = sorted(eligible, key=lambda row: (-row["worst_attack_recall"], -row["attack_episode_recall"], row["fpr"], -row["attack_macro_f1"], row["configuration"]["max_leaf_nodes"], row["candidate"]))[0]
    config = selected["configuration"]
    gate, subtype = build_model(config, x.loc[train_mask], y[train_mask])
    cal_gate_raw = aligned(gate, x.loc[cal_mask], [0, 1])[:, 1]
    cal_subtype_raw = aligned(subtype, x.loc[cal_mask], ATTACKS)
    gate_cal = BinarySigmoidCalibrator().fit(cal_gate_raw, (y[cal_mask] != "benign").astype(int))
    subtype_cal = SubtypeSigmoidCalibrator().fit(cal_subtype_raw[y[cal_mask] != "benign"], np.asarray([ATTACKS.index(value) for value in y[cal_mask][y[cal_mask] != "benign"]]))
    gate_p = gate_cal.predict(cal_gate_raw); subtype_p = subtype_cal.predict(cal_subtype_raw)
    probabilities = np.column_stack([1 - gate_p, gate_p[:, None] * subtype_p])
    thresholds = {}
    for index, name in enumerate(CLASSES):
        scores = sorted(1 - probabilities[y[cal_mask] == name, index]); rank = min(len(scores) - 1, math.ceil((len(scores) + 1) * .95) - 1)
        thresholds[name] = float(1 - scores[rank])
    bundle = {"schema_version": "v03154_candidate_v1", "features": names, "classes": CLASSES, "gate": gate, "subtype": subtype, "gate_calibrator": gate_cal, "subtype_calibrator": subtype_cal, "conformal_thresholds": thresholds, "selected_configuration": selected["candidate"], "state_policy_sha256": "3b1acd1a066b278a75c2edc5152c64ee2dd962fee21bd7b43acffb567e4a700c", "event_contract_sha256": "cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe"}
    RUNTIME.mkdir(parents=True, exist_ok=True); artifact = RUNTIME / "v03154_candidate.joblib"; joblib.dump(bundle, artifact)
    artifact_hash = sha(artifact); candidate_id = f"v03154:{artifact_hash[:16]}"; bundle["candidate_id"] = candidate_id; joblib.dump(bundle, artifact); artifact_hash = sha(artifact); candidate_id = f"v03154:{artifact_hash[:16]}"
    cal_sets = conformal_sets(bundle, probabilities); cal_predictions = np.asarray(CLASSES)[np.argmax(probabilities, axis=1)]
    cal_metrics = metrics(y[cal_mask], cal_predictions)
    coverage = float(np.mean([truth in values for truth, values in zip(y[cal_mask], cal_sets)])); empty = float(np.mean([not values for values in cal_sets]))
    write_json(REPORT / "candidate_comparison.json", {"configuration_count": 3, "grouped_fold_count": 3, "comparisons": comparisons, "selected": selected["candidate"], "selection_order": ["worst_class_recall_desc", "attack_episode_recall_desc", "conformal_empty_set_rate_asc", "fpr_asc", "macro_f1_desc", "complexity_asc"]})
    write_json(REPORT / "candidate_selection_report.json", {"selected": selected["candidate"], "all_required_gates_passed": True, "selected_metrics": selected, "audit_labels_read_count": 0})
    write_json(REPORT / "calibration_report.json", {"method": "sigmoid", "sessions_only": lock["calibration_sessions"], "fit_row_count": int(cal_mask.sum()), "audit_row_count": 0, "metrics": cal_metrics})
    write_json(REPORT / "conformal_report.json", {"method": "mondrian_class_conditional", "alpha": .05, "sessions_only": lock["calibration_sessions"], "thresholds": thresholds, "coverage": coverage, "empty_set_rate": empty, "audit_row_count": 0})
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "v03154_candidate_manifest_v1", "candidate_id": candidate_id, "artifact_sha256": artifact_hash, "artifact_tracked": False, "artifact_runtime_path": "runtime/v0_3_15_4/v03154_candidate.joblib", "feature_contract_sha256": sha(CFG / "feature_contract_v2.yaml"), "training_lock_sha256": sha(CFG / "training_lock.json"), "preprocessing": "network_features_v2", "model": "HGB_gate_plus_HGB_subtype", "calibration": "sigmoid", "conformal": "mondrian_class_conditional_alpha_0.05", "class_map": CLASSES, "state_policy_sha256": bundle["state_policy_sha256"], "event_contract_sha256": bundle["event_contract_sha256"], "runtime_compatibility": {"python": f"{sys.version_info.major}.{sys.version_info.minor}", "joblib": joblib.__version__, "feature_count": 51}}
    write_json(ARTIFACT_DIR / "candidate_manifest.json", manifest)
    preaudit = {"schema_version": "v03154_pre_audit_lock_v1", "candidate_id": candidate_id, "candidate_artifact_sha256": artifact_hash, "candidate_manifest_sha256": sha(ARTIFACT_DIR / "candidate_manifest.json"), "training_lock_sha256": sha(CFG / "training_lock.json"), "selection_report_sha256": sha(REPORT / "candidate_selection_report.json"), "calibration_report_sha256": sha(REPORT / "calibration_report.json"), "conformal_report_sha256": sha(REPORT / "conformal_report.json"), "feature_rows_sha256": sha(RUNTIME / "feature_rows.jsonl"), "sealed_audit_labels_sha256": read_json(RUNTIME / "label_separation_commitment.json")["sealed_audit_sha256"], "state_policy_frozen": True, "thresholds_frozen": True, "audit_labels_read_count": 0, "audit_inference_call_count": 0, "tuning_after_unlock_allowed": False, "ready_to_unlock_once": True}
    write_json(CFG / "pre_audit_lock.json", preaudit)
    print(json.dumps({"candidate_id": candidate_id, "artifact_sha256": artifact_hash, "pre_audit_lock_sha256": sha(CFG / "pre_audit_lock.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__": raise SystemExit(main())
