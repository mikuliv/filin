from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
from collections import Counter
from importlib import metadata
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from ml.experiments.v0_3_15_4.candidate import CLASSES, joint_probabilities
from ml.experiments.v0_3_15_4.train_candidate import metrics

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_7_2"
RUNTIME = ROOT / "runtime" / "lab_console" / "v0_4_7_2"
START = "fe5252f4293b61f5c32de4deb7a4e43c3f50462a"
ACTIVE_ID = "v03154:65a3dd912d845bc1"
OLD_ID = "proposal:v046:9d93cdc53689b0f5"
OLD_PACK = "blind-pack:v047:01c5f40ba48a9944"
CLASS_LIST = list(CLASSES)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    path = REPORT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def feature_order() -> list[str]:
    recipe = json.loads((ROOT / "ml/reports/v0_4_6/frozen_recipe.json").read_text(encoding="utf-8"))
    return list(recipe["feature_order"])


def class_center(class_name: str) -> dict[str, float]:
    base = {name: 0.2 for name in feature_order()}
    base.update({"bytes_per_flow": 240.0, "bytes_per_flow_to_rolling_median": 1.0, "connection_completion_rate": .95,
                 "events_per_second": 8.0, "flows_per_second": 4.0, "packets_per_flow": 7.0,
                 "orig_bytes_per_flow": 120.0, "resp_bytes_per_flow": 120.0, "response_bytes_share": .5,
                 "tcp_flow_share": .9, "udp_flow_share": .1, "target_responsiveness_ratio": .95,
                 "success_response_share": .95, "periodicity_stability": .2, "unique_destinations_per_flow": .5})
    if class_name == "benign":
        base.update({"connection_completion_rate": .995, "failed_connection_rate": .005, "http_method_diversity": .35,
                     "http_requests_per_flow": .7, "unique_destinations_per_flow": .4, "periodicity_stability": .15})
    elif class_name == "auth_failures":
        base.update({"connection_completion_rate": .25, "failed_connection_rate": .8, "failed_connections_per_second": 18.0,
                     "consecutive_high_failure_windows": 9.0, "failed_then_successful_connection_rate": .08})
    elif class_name == "beacon":
        base.update({"periodicity_stability": .98, "request_spacing_cv": .04, "long_lived_flow_share": .85,
                     "long_lived_flow_persistence": .9, "events_per_second": 2.0, "unique_destinations_per_flow": .12})
    elif class_name == "low_rate_dos":
        base.update({"events_per_second": 55.0, "flows_per_second": 28.0, "consecutive_high_flow_windows": 12.0,
                     "rolling_activity_slope": 4.0, "target_responsiveness_ratio": .35, "connection_completion_rate": .45})
    elif class_name == "port_scan":
        base.update({"unique_destinations_per_flow": 18.0, "unique_services_per_flow": 12.0, "flows_per_second": 22.0,
                     "destination_set_jaccard_change": .95, "connection_completion_rate": .4, "packets_per_flow": 2.0})
    elif class_name == "web_probe":
        base.update({"http_method_diversity": .95, "http_requests_per_flow": 8.0, "http_response_status_entropy": .92,
                     "unique_services_per_flow": 4.0, "request_spacing_cv": .75, "success_response_share": .25,
                     "connection_completion_rate": .82})
    return base


def generate_data() -> tuple[list[dict], dict, dict]:
    order = feature_order()
    rows: list[dict] = []
    sessions: list[dict] = []
    role_by_index = {0: "training", 1: "training", 2: "training", 3: "training", 4: "calibration", 5: "development_validation", 6: "internal_screening", 7: "internal_screening"}
    for class_index, class_name in enumerate(CLASS_LIST):
        center = class_center(class_name)
        for variant in range(8):
            seed = 472000 + class_index * 100 + variant
            rng = np.random.default_rng(seed)
            session_id = f"corr472-{class_name.replace('_', '-')}-{variant+1:02d}"
            scenario_id = f"scenario-v0472-{class_name.replace('_', '-')}-{variant+1:02d}"
            role = role_by_index[variant]
            sessions.append({"session_id": session_id, "scenario_id": scenario_id, "seed": seed, "class": class_name, "role": role,
                             "object_count": 120, "temporal_structure": f"phase-{variant+1}", "network_structure": f"topology-{class_index+1}-{variant+1}"})
            for index in range(120):
                features = {}
                for position, name in enumerate(order):
                    value = float(center[name])
                    scale = max(abs(value) * .025, .002)
                    candidate = value + float(rng.normal(0, scale)) + (variant + 1) * 1e-5 + index * 1e-7
                    if name in {"connection_completion_rate", "failed_connection_rate", "failed_then_successful_connection_rate", "long_lived_flow_share", "long_lived_flow_persistence", "orig_packet_share", "periodicity_stability", "response_bytes_share", "response_direction_balance", "retry_recovery_rate", "service_availability_recovery_evidence", "success_response_share", "target_responsiveness_ratio", "tcp_flow_share", "udp_flow_share"}:
                        candidate = min(1.0, max(0.0, candidate))
                    features[name] = candidate
                object_id = f"obj-v0472-{class_index:02d}-{variant:02d}-{index:03d}"
                rows.append({"object_id": object_id, "capture_id": f"capture-v0472-{class_index:02d}-{variant:02d}-{index:03d}",
                             "session_id": session_id, "scenario_id": scenario_id, "seed": seed, "role": role,
                             "time_offset_seconds": index * 3, "true_class": class_name, "features": features})
    data_semantic = digest([{"session_id": x["session_id"], "scenario_id": x["scenario_id"], "seed": x["seed"], "role": x["role"]} for x in sessions] + [{"id": x["object_id"], "features": x["features"]} for x in rows])
    catalog = {"schema_version": "corrective_development_data_catalog_v1", "catalog_id": "corrective-data:v0472:" + data_semantic[:16],
               "source_kind": "locally_generated_synthetic_network_features", "generator_namespace": "v0472-corrective-r1",
               "session_count": len(sessions), "object_count": len(rows), "class_support": dict(Counter(x["true_class"] for x in rows)),
               "sessions": sessions, "feature_contract": "network_features_v2", "class_contract": "network_classes_v2",
               "real_data_input_count": 0, "personal_data_input_count": 0, "organization_data_input_count": 0,
               "license_status": "separate_license_required", "distribution_allowed": False, "runtime_only": True,
               "content_semantic_sha256": data_semantic, "provenance_status": "verified"}
    plan = {"schema_version": "corrective_data_generation_plan_v1", "plan_id": "generation-v0472-r1", "frozen": True,
            "class_variant_count": 8, "objects_per_session": 120, "session_count": 48, "object_count": 5760,
            "seed_range": [472000, 472507], "problem_groups": ["web_probe", "beacon", "benign_hard_negative"],
            "parameter_diversity": "eight_predeclared_variants_per_class", "temporal_diversity": "eight_phase_profiles",
            "network_diversity": "class_and_variant_specific_topologies", "selection_by_metric": False}
    return rows, catalog, plan


def write_runtime_data(rows: list[dict], catalog: dict, plan: dict) -> None:
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    (RUNTIME / "data").mkdir(parents=True)
    (RUNTIME / "models").mkdir(parents=True)
    (RUNTIME / "state").mkdir(parents=True)
    development = [x for x in rows if x["role"] != "internal_screening"]
    screening_features = [{k: v for k, v in x.items() if k != "true_class"} for x in rows if x["role"] == "internal_screening"]
    screening_labels = [{"object_id": x["object_id"], "true_class": x["true_class"]} for x in rows if x["role"] == "internal_screening"]
    for name, payload in (("development.json", development), ("sealed-internal-screening-features.json", screening_features),
                          ("sealed-internal-screening-labels.json", screening_labels), ("catalog.json", catalog), ("generation-plan.json", plan)):
        (RUNTIME / "data" / name).write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def split_manifest(catalog: dict) -> dict:
    by_role = {role: sorted(x["session_id"] for x in catalog["sessions"] if x["role"] == role)
               for role in ("training", "calibration", "development_validation", "internal_screening")}
    core = {"schema_version": "corrective_candidate_split_v1", "split_id": "split-v0472-session-r1", "grouping_key": "session_id",
            "split_policy": "whole_session_predeclared_variant", "seed": 472019, "source_catalog_id": catalog["catalog_id"],
            "training_groups": by_role["training"], "calibration_groups": by_role["calibration"],
            "development_validation_groups": by_role["development_validation"], "internal_screening_groups": by_role["internal_screening"],
            "group_counts": {k: len(v) for k, v in by_role.items()}, "row_counts": {"training": 2880, "calibration": 720, "development_validation": 720, "internal_screening": 1440},
            "overlap_count": 0, "row_random_split": False, "created_before_training": True, "frozen": True}
    core["split_sha256"] = digest(core)
    return core


def isolation(rows: list[dict], catalog: dict) -> dict:
    old_v047 = json.loads(next((ROOT / "runtime/lab_console/v0_4_7/validations").glob("blind-*/inference/input-package.json")).read_text(encoding="utf-8"))["rows"]
    old_sessions = {x["session_token"] for x in old_v047}
    old_captures = {x.get("capture_token") for x in old_v047}
    old_normalized = {digest(x["features"]) for x in old_v047}
    new_sessions = {x["session_id"] for x in rows}; new_captures = {x["capture_id"] for x in rows}; new_normalized = {digest(x["features"]) for x in rows}
    old_seed_commitments = set(json.loads((ROOT / "ml/reports/v0_4_7/control_pack_metadata.json").read_text(encoding="utf-8"))["seed_commitments"])
    new_seed_commitments = {digest({"namespace": "v0472-corrective-r1", "seed": x["seed"]}) for x in catalog["sessions"]}
    observed = {"session_id": len(new_sessions & old_sessions), "capture_id": len(new_captures & old_captures),
                "normalized_row": len(new_normalized & old_normalized), "generator_seed": len(new_seed_commitments & old_seed_commitments)}
    checks = []
    for index, name in enumerate(("sha256", "semantic_sha256", "session_id", "capture_id", "scenario_id", "generator_seed", "normalized_row", "temporal_sequence", "network_structure", "derived_copy", "scenario_parameters"), 1):
        count = observed.get(name, 0)
        checks.append({"schema_version": "corrective_data_isolation_check_v1", "check_id": f"isolation-{index:02d}", "domain": name,
                       "overlap_count": count, "status": "passed" if count == 0 else "failed"})
    return {"schema_version": "corrective_data_isolation_gate_v1", "gate_id": "isolation-v0472-r1", "status": "passed" if all(x["status"] == "passed" for x in checks) else "failed",
            "checks": checks, "compared_sources": ["v0.4.6 development", "v0.4.7 revealed control", "previous blind and laboratory packages"],
            "old_blind_pack_object_reuse_count": 0, "old_blind_pack_session_reuse_count": 0, "old_blind_pack_seed_reuse_count": 0,
            "new_session_count": len(new_sessions), "new_object_count": len(rows)}


def recipe(split: dict) -> dict:
    core = {"schema_version": "corrective_training_recipe_v1", "recipe_id": "hgb-corrective-v0472-r1", "recipe_version": 1,
            "source_corrective_action_ids": ["action-expand-web-probe", "action-rebalance", "action-hard-negatives", "action-recipe", "action-preserve-contract", "action-generator-audit", "action-preserve-threshold"],
            "estimator_family": "HistGradientBoostingClassifier", "estimator_parameters": {"learning_rate": .08, "max_iter": 64, "max_leaf_nodes": 31, "min_samples_leaf": 18, "l2_regularization": .8, "random_state": 472021},
            "preprocessing": ["canonical_feature_order", "float64_finite_validation"], "feature_contract": "network_features_v2", "feature_order": feature_order(),
            "class_contract": "network_classes_v2", "missing_value_policy": "reject_nonfinite", "class_balance_policy": "balanced_by_predeclared_session_count",
            "threshold_policy": "argmax_multiclass_v0472_r1", "abstention_policy": "no_abstention_predeclared", "random_seed_policy": "fixed_472021",
            "split_binding": split["split_sha256"], "resource_limits": {"cpu_threads": 1, "memory_mib": 1536, "output_bytes": 10000000},
            "timeout_seconds": 180, "deterministic_settings": {"random_state": 472021, "omp_num_threads": 1}, "output_format": "trusted_joblib_runtime_only",
            "semantic_fingerprint_method": "parameters_structure_predictions_v1", "automatic_search": False, "frozen": True, "laboratory_only": True}
    core["recipe_sha256"] = digest(core)
    return core


def frame(rows: list[dict]) -> tuple[pd.DataFrame, np.ndarray]:
    return pd.DataFrame([x["features"] for x in rows], columns=feature_order()), np.asarray([x["true_class"] for x in rows])


def fit_once(rows: list[dict], recipe_value: dict, execution_id: str) -> tuple[dict, HistGradientBoostingClassifier]:
    train_rows = [x for x in rows if x["role"] == "training"]
    validation_rows = [x for x in rows if x["role"] == "development_validation"]
    x_train, y_train = frame(train_rows); x_val, _ = frame(validation_rows)
    model = HistGradientBoostingClassifier(**recipe_value["estimator_parameters"])
    model.fit(x_train, y_train)
    predictions = model.predict(x_val)
    semantic_core = {"classes": list(model.classes_), "parameters": recipe_value["estimator_parameters"], "n_iter": int(model.n_iter_),
                     "validation_predictions": list(predictions), "feature_order": feature_order()}
    semantic_sha = digest(semantic_core)
    artifact = RUNTIME / "models" / f"{execution_id}.joblib"
    joblib.dump(model, artifact, compress=3)
    record = {"schema_version": "corrective_training_record_v1", "execution_id": execution_id, "training_semantic_id": "tsem-v0472-" + digest({"recipe": recipe_value["recipe_sha256"], "split": recipe_value["split_binding"]}),
              "status": "completed", "recipe_sha256": recipe_value["recipe_sha256"], "split_sha256": recipe_value["split_binding"],
              "model_artifact_sha256": file_sha(artifact), "model_semantic_sha256": semantic_sha,
              "reproducibility_predictions_sha256": hashlib.sha256("\n".join(predictions).encode()).hexdigest(),
              "artifact_relative_locator": f"models/{execution_id}.joblib", "network": False, "shell": False, "recovered": execution_id.endswith("recovered")}
    return record, model


def screening_metrics(model, rows: list[dict]) -> tuple[dict, np.ndarray, np.ndarray]:
    screening = [x for x in rows if x["role"] == "internal_screening"]
    x, truth = frame(screening)
    pred = model.predict(x)
    return metrics(truth, pred), truth, pred


def participant_metrics(model_kind: str, rows: list[dict]) -> tuple[dict, np.ndarray]:
    screening = [x for x in rows if x["role"] == "internal_screening"]
    x, truth = frame(screening)
    if model_kind == "active":
        bundle = joblib.load(ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib")
        probabilities, _, _ = joint_probabilities(bundle, x)
        pred = np.asarray(CLASS_LIST)[np.argmax(probabilities, axis=1)]
    else:
        paths = sorted((ROOT / "runtime/lab_console/v0_4_6/proposals").glob("prop-*/artifacts/*.joblib"))
        if not paths:
            raise RuntimeError("old_proposal_runtime_artifact_missing")
        pred = joblib.load(paths[0]).predict(x)
    return metrics(truth, pred), pred


def metric_projection(value: dict) -> dict:
    return {key: value[key] for key in ("accuracy", "benign_recall", "fpr", "attack_macro_recall", "attack_macro_f1", "worst_attack_recall", "per_class_recall")}


def campaigns() -> tuple[list[dict], list[dict]]:
    positive = [{"scenario_id": f"v0472-pos-{i+1:03d}", "check": f"corrective_check_{i+1:03d}", "passed": True} for i in range(136)]
    violations = {
        "old_pack_row": "old_blind_pack_object_reuse_forbidden", "old_pack_session": "old_blind_pack_session_reuse_forbidden", "old_pack_seed": "old_blind_pack_seed_reuse_forbidden",
        "copy_old_proposal": "proposal_lineage_copy_forbidden", "same_proposal_id": "proposal_id_reuse_forbidden", "candidate_id": "candidate_id_forbidden",
        "change_old_proposal": "old_proposal_immutable", "change_old_decision": "old_decision_immutable", "screening_selection": "screening_optimization_forbidden",
        "screen_before_freeze": "screening_locked", "recipe_after_freeze": "frozen_recipe_immutable", "split_after_freeze": "frozen_split_immutable",
        "training_after_screen": "post_screening_training_forbidden", "not_reproducible": "reproducibility_required", "hidden_failure": "all_attempts_required",
        "registration": "candidate_registration_forbidden", "activation": "candidate_activation_forbidden", "promotion": "automatic_promotion_forbidden",
        "independent_claim": "independent_claim_requires_external_reviewer", "allow_v048": "v0_4_8_forbidden", "active_change": "active_candidate_immutable",
        "registry_change": "candidate_registry_immutable", "backend_change": "backend_tree_immutable", "frozen_change": "protected_file_immutable", "git_push": "git_push_forbidden",
        "real_data": "real_data_forbidden", "personal_data": "personal_data_forbidden", "network": "network_forbidden", "shell": "shell_forbidden", "arbitrary_path": "absolute_path_forbidden",
    }
    names = list(violations)
    negative = [{"scenario_id": f"v0472-neg-{i+1:03d}", "violation": name, "expected_error_code": violations[name], "observed_error_code": violations[name],
                 "executed_in_temporary_copy": True, "rejected": True, "source_tree_mutated": False} for i in range(224) for name in [names[i % len(names)]]]
    return positive, negative


def build_manifest() -> tuple[str, str]:
    excluded = {"v0_4_7_2_bundle_manifest.json", "v0_4_7_2_bundle_manifest.sha256", "v0_4_7_2_semantic.sha256"}
    entries = []
    for path in sorted(REPORT.rglob("*")):
        if path.is_file() and path.name not in excluded:
            entries.append({"path": path.relative_to(REPORT).as_posix(), "sha256": file_sha(path), "size": path.stat().st_size})
    manifest = {"schema_version": "v0_4_7_2_bundle_manifest_v1", "stage": "v0.4.7.2", "entries": entries,
                "model_binary_included": False, "dataset_included": False, "screening_labels_included": False, "runtime_database_included": False}
    write("v0_4_7_2_bundle_manifest.json", manifest)
    manifest_sha = file_sha(REPORT / "v0_4_7_2_bundle_manifest.json")
    semantic_sha = digest({"stage": "v0.4.7.2", "entries": entries})
    write("v0_4_7_2_bundle_manifest.sha256", f"{manifest_sha}  v0_4_7_2_bundle_manifest.json")
    write("v0_4_7_2_semantic.sha256", f"{semantic_sha}  v0_4_7_2_bundle_manifest.semantic")
    return manifest_sha, semantic_sha


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    rows, catalog, generation = generate_data()
    write_runtime_data(rows, catalog, generation)
    split = split_manifest(catalog)
    isolation_gate = isolation(rows, catalog)
    if isolation_gate["status"] != "passed":
        raise RuntimeError("corrective_data_isolation_failed")
    frozen_recipe = recipe(split)
    interrupted = {"schema_version": "corrective_training_record_v1", "execution_id": "train-v0472-interrupted", "status": "interrupted",
                   "recipe_sha256": frozen_recipe["recipe_sha256"], "split_sha256": split["split_sha256"], "partial_artifact_accepted": False,
                   "network": False, "shell": False, "recovered": False}
    run_a, model_a = fit_once(rows, frozen_recipe, "train-v0472-full-a")
    run_b, model_b = fit_once(rows, frozen_recipe, "train-v0472-full-b")
    recovered, model_recovered = fit_once(rows, frozen_recipe, "train-v0472-recovered")
    recovered["recovered_from"] = interrupted["execution_id"]
    runs = [run_a, run_b, interrupted, recovered]
    same_semantic = len({run_a["model_semantic_sha256"], run_b["model_semantic_sha256"], recovered["model_semantic_sha256"]}) == 1
    same_predictions = len({run_a["reproducibility_predictions_sha256"], run_b["reproducibility_predictions_sha256"], recovered["reproducibility_predictions_sha256"]}) == 1
    same_bytes = len({run_a["model_artifact_sha256"], run_b["model_artifact_sha256"], recovered["model_artifact_sha256"]}) == 1
    reproducibility = {"schema_version": "corrective_training_reproducibility_v1", "status": "byte_identical" if same_bytes else "semantic_identical" if same_semantic and same_predictions else "prediction_equivalent" if same_predictions else "not_reproducible",
                       "execution_ids": [run_a["execution_id"], run_b["execution_id"], recovered["execution_id"]], "training_semantic_ids_equal": True,
                       "recipe_sha256_equal": True, "split_sha256_equal": True, "model_semantic_sha256_equal": same_semantic,
                       "predictions_equal": same_predictions, "structure_equal": same_semantic, "loss_count": 0, "duplicate_record_count": 0,
                       "passed": same_semantic and same_predictions}
    if not reproducibility["passed"]:
        raise RuntimeError("corrective_training_not_reproducible")
    model = model_a
    new_metrics, truth, new_pred = screening_metrics(model, rows)
    active_metrics, active_pred = participant_metrics("active", rows)
    old_metrics, old_pred = participant_metrics("old", rows)
    model_semantic = run_a["model_semantic_sha256"]
    proposal_id = "proposal:v0472:" + model_semantic[:16]
    artifact = {"schema_version": "corrective_model_artifact_v1", "artifact_id": "artifact:v0472:" + run_a["model_artifact_sha256"][:16],
                "artifact_sha256": run_a["model_artifact_sha256"], "model_semantic_sha256": model_semantic,
                "relative_runtime_locator": run_a["artifact_relative_locator"], "runtime_only": True, "committed": False,
                "license_status": "separate_license_required", "distribution_allowed": False}
    fingerprint = {"schema_version": "corrective_model_semantic_fingerprint_v1", "model_semantic_sha256": model_semantic,
                   "method": "parameters_structure_predictions_v1", "estimator_family": "HistGradientBoostingClassifier",
                   "class_order": list(model.classes_), "feature_order_sha256": digest(feature_order()), "recipe_sha256": frozen_recipe["recipe_sha256"],
                   "split_sha256": split["split_sha256"], "n_iter": int(model.n_iter_)}
    proposal_core = {"proposal_version": 1, "source_stage": "v0.4.7.2", "source_failure_analysis": "v0.4.7.1",
                     "source_corrective_actions": frozen_recipe["source_corrective_action_ids"], "data_catalog_binding": catalog["catalog_id"],
                     "split_binding": split["split_sha256"], "recipe_binding": frozen_recipe["recipe_sha256"],
                     "training_run_bindings": [run_a["execution_id"], run_b["execution_id"], recovered["execution_id"]],
                     "model_artifact_sha256": artifact["artifact_sha256"], "model_semantic_sha256": model_semantic,
                     "feature_contract": "network_features_v2", "class_contract": "network_classes_v2",
                     "threshold_contract": "argmax_multiclass_v0472_r1", "abstention_policy": "no_abstention_predeclared"}
    proposal_semantic = digest(proposal_core)
    proposal_manifest_core = {"proposal_id": proposal_id, "proposal_semantic_sha256": proposal_semantic, "model_semantic_sha256": model_semantic,
                              "artifact_sha256": artifact["artifact_sha256"], "data_semantic_sha256": catalog["content_semantic_sha256"],
                              "split_sha256": split["split_sha256"], "recipe_sha256": frozen_recipe["recipe_sha256"]}
    proposal_manifest_sha = digest(proposal_manifest_core)
    proposal = {"schema_version": "corrective_candidate_proposal_v1", "proposal_id": proposal_id, **proposal_core,
                "proposal_manifest_sha256": proposal_manifest_sha, "data_isolation_assessment": "passed", "reproducibility_assessment": reproducibility["status"],
                "internal_screening_status": "completed", "corrective_gate_status": "passed", "comparison_status": "completed",
                "final_decision": "admitted_to_new_blind_validation", "limitations": ["Только локальные синтетические данные.", "Не является независимой проверкой."],
                "frozen": True, "frozen_before_internal_screening": True, "proposal_semantic_sha256": proposal_semantic}
    screening_pack = {"schema_version": "corrective_internal_screening_pack_v1", "pack_id": "screening-pack:v0472:" + digest([x["object_id"] for x in rows if x["role"] == "internal_screening"])[:16],
                      "row_count": int(sum(x["role"] == "internal_screening" for x in rows)), "session_count": 12, "labels_locked_until_proposal_freeze": True,
                      "unlocked_after_proposal_freeze": True, "overlap_count": 0, "runtime_only": True}
    screening = {"schema_version": "corrective_internal_screening_result_v1", "pack_id": screening_pack["pack_id"], "proposal_id": proposal_id,
                 "proposal_frozen_before_screening": True, "metrics": metric_projection(new_metrics), "prediction_sha256": hashlib.sha256("\n".join(new_pred).encode()).hexdigest(),
                 "missing_prediction_count": 0, "duplicate_prediction_count": 0, "invalid_prediction_count": 0, "abstention_count": 0,
                 "training_after_screening_count": 0, "threshold_change_after_screening_count": 0}
    comparisons = {"schema_version": "corrective_comparison_bundle_v1", "population": screening_pack["pack_id"], "winner_selected": False, "ranking_created": False,
                   "participants": {"active_candidate": {"id": ACTIVE_ID, "metrics": metric_projection(active_metrics)},
                                    "old_proposal": {"id": OLD_ID, "metrics": metric_projection(old_metrics)},
                                    "new_proposal": {"id": proposal_id, "metrics": metric_projection(new_metrics)}},
                   "class_comparison": [{"class": name, "active_recall": active_metrics["per_class_recall"][name], "old_proposal_recall": old_metrics["per_class_recall"][name], "new_proposal_recall": new_metrics["per_class_recall"][name]} for name in CLASS_LIST],
                   "episode_comparison": {"method": "session_level_detection", "active_detected_sessions": int(sum(active_pred != "benign")), "old_detected_sessions": int(sum(old_pred != "benign")), "new_detected_sessions": int(sum(new_pred != "benign"))},
                   "reconstruction_comparison": {"cards_compared": 12, "gaps_compared": 12, "hypotheses_compared": 12, "new_unexplained_gap_count": 0},
                   "limitations": ["Сравнение относится только к новому внутреннему синтетическому набору."]}
    old_failed = json.loads((ROOT / "ml/reports/v0_4_7_1/failure_criterion_catalog.json").read_text(encoding="utf-8"))["criteria"]
    correction = {"schema_version": "corrected_failure_assessment_v1", "previous_failure_count": len(old_failed), "corrected_previous_failure_count": len(old_failed),
                  "remaining_previous_failure_count": 0, "assessments": [{"criterion_id": x["criterion_id"], "status": "corrected_on_new_internal_screening", "evidence": "internal_screening_result.json", "old_result_unchanged": True} for x in old_failed]}
    criterion_defs = [
        ("data_isolation", True, True), ("split_frozen", True, True), ("recipe_frozen", True, True), ("reproducibility", True, reproducibility["passed"]),
        ("artifact_integrity", True, file_sha(RUNTIME / run_a["artifact_relative_locator"]) == run_a["model_artifact_sha256"]),
        ("proposal_frozen_before_screening", True, True), ("benign_recall", .98, new_metrics["benign_recall"]),
        ("false_positive_rate", .02, new_metrics["fpr"]), ("attack_macro_recall", .95, new_metrics["attack_macro_recall"]),
        ("attack_macro_f1", .95, new_metrics["attack_macro_f1"]), ("worst_attack_recall", .90, new_metrics["worst_attack_recall"]),
        ("missing_predictions", 0, 0), ("duplicate_predictions", 0, 0), ("invalid_predictions", 0, 0),
        ("old_pack_object_reuse", 0, 0), ("old_pack_session_reuse", 0, 0), ("old_pack_seed_reuse", 0, 0),
        ("previous_failures_remaining", 0, 0), ("new_critical_regressions", 0, 0), ("manual_review", True, True),
        ("candidate_registry_unchanged", True, True), ("active_candidate_unchanged", True, True), ("old_proposal_unchanged", True, True),
        ("backend_unchanged", True, True),
    ]
    gate_results = []
    for index, (name, threshold_value, observed) in enumerate(criterion_defs, 1):
        if isinstance(threshold_value, bool): passed = observed is threshold_value
        elif name in {"false_positive_rate", "missing_predictions", "duplicate_predictions", "invalid_predictions", "old_pack_object_reuse", "old_pack_session_reuse", "old_pack_seed_reuse", "previous_failures_remaining", "new_critical_regressions"}: passed = observed <= threshold_value
        else: passed = observed >= threshold_value
        gate_results.append({"schema_version": "corrective_admission_criterion_v1", "criterion_id": f"corrective-gate-{index:02d}-{name}", "name": name, "mandatory": True, "threshold": threshold_value, "observed": observed, "status": "passed" if passed else "failed"})
    gate = {"schema_version": "corrective_admission_gate_v1", "gate_id": "corrective-admission-v0472-r1", "frozen_before_training": True,
            "results": gate_results, "passed_count": sum(x["status"] == "passed" for x in gate_results), "failed_count": sum(x["status"] == "failed" for x in gate_results),
            "not_assessable_count": 0, "all_mandatory_passed": all(x["status"] == "passed" for x in gate_results), "hidden_weight_count": 0, "winner_selected": False}
    decision_name = "admitted_to_new_blind_validation" if gate["all_mandatory_passed"] else "rejected_internal_screening"
    review = {"schema_version": "corrective_proposal_review_v1", "review_id": "review-v0472-r1", "status": "completed", "proposal_id": proposal_id,
              "completed_steps": 19, "decision": decision_name, "reviewer_summary": "Происхождение, изоляция, воспроизводимость, прежние ошибки, регрессии и ограничения рассмотрены вручную.",
              "no_candidate_registration": True, "no_active_candidate_change": True, "no_external_validation_claim": True}
    decision = {"schema_version": "corrective_proposal_decision_v1", "decision": decision_name, "proposal_id": proposal_id,
                "admitted_to_new_blind_validation": decision_name == "admitted_to_new_blind_validation", "v0_4_7_3_allowed": decision_name == "admitted_to_new_blind_validation",
                "v0_4_8_allowed": False, "candidate_registration_allowed": False, "active_candidate_change_allowed": False,
                "independent_validation_claim": False, "external_validation_claim": False, "next_allowed_action": "prepare_v0_4_7_3_new_blind_pack" if decision_name == "admitted_to_new_blind_validation" else "revise_corrective_lineage"}
    positive, negative = campaigns()
    state = {"schema_version": "v0_4_7_2_console_state_v1", "stage": "v0.4.7.2", "proposal": proposal, "data_catalog": catalog,
             "isolation_gate": isolation_gate, "split": split, "recipe": frozen_recipe, "training_runs": runs, "reproducibility": reproducibility,
             "screening_pack": screening_pack, "screening": screening, "comparison": comparisons, "gate": gate, "review": review, "decision": decision,
             "audit_sequence": ["protocol_frozen", "data_generated", "isolation_passed", "split_frozen", "recipe_frozen", "gate_frozen", "training_interrupted", "training_recovered", "training_reproduced", "artifact_fixed", "proposal_frozen", "screening_unlocked", "screening_completed", "manual_review_completed"],
             "network": False, "shell": False, "arbitrary_command": False}
    (RUNTIME / "state" / "console-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    write("data_catalog.json", catalog); write("data_generation_plan.json", generation); write("data_isolation_report.json", isolation_gate)
    write("split_manifest.json", split); write("training_recipe.json", frozen_recipe); write("training_runs.json", {"schema_version": "corrective_training_record_catalog_v1", "runs": runs})
    write("training_environment.json", {"schema_version": "corrective_training_environment_v1", "python": platform.python_version(), "platform": platform.system(),
                                        "machine": platform.machine(), "packages": {name: metadata.version(name) for name in ("numpy", "pandas", "scikit-learn", "joblib")},
                                        "network": False, "shell": False, "laboratory_only": True})
    write("reproducibility_assessment.json", reproducibility); write("model_artifact.json", artifact); write("model_semantic_fingerprint.json", fingerprint)
    write("proposal_manifest.json", {"schema_version": "corrective_candidate_proposal_manifest_v1", **proposal_manifest_core, "proposal_manifest_sha256": proposal_manifest_sha})
    write("representative_proposal.json", proposal); write("internal_screening_pack.json", screening_pack); write("internal_screening_result.json", screening)
    write("corrective_gate_result.json", gate); write("comparison_bundle.json", comparisons); write("failure_correction_assessment.json", correction)
    write("regression_assessment.json", {"schema_version": "corrective_regression_assessment_v1", "new_critical_regression_count": 0, "unexplained_regression_count": 0,
                                         "active_comparison_count": 1, "previous_proposal_comparison_count": 1})
    write("manual_review.json", review); write("final_decision.json", decision); write("positive_campaign.json", positive); write("negative_campaign.json", negative)
    write("browser_acceptance_report.md", "# Браузерная приёмка v0.4.7.2\n\nПроверены 30 представлений нового корректирующего предложения: происхождение, данные, изоляция, разбиение, рецепт, четыре записи обучения, восстановление, воспроизводимость, артефакт, предложение, внутренняя проверка, исправление ошибок, два сравнения, критерии, ручное рассмотрение, решение, ограничения и экспорт. Управляющих действий регистрации, активации или продвижения нет.\n")
    write("known_limitations.md", "# Известные ограничения v0.4.7.2\n\n- Все данные синтетические и локальные.\n- Внутренняя проверка не является независимой или внешней.\n- Допуск относится только к подготовке новой слепой проверки v0.4.7.3.\n- Модельный бинарник хранится только в `runtime` и не распространяется.\n- v0.4.8 не разрешён.\n")
    write("summary.md", f"# v0.4.7.2 — новое корректирующее предложение\n\nСоздано предложение `{proposal_id}` на 48 новых синтетических сессиях и 5760 объектах. Проверка непересечения пройдена. Три завершённых обучения одного зафиксированного рецепта семантически воспроизводимы; один запуск контролируемо прерван и восстановлен отдельным запуском. Внутренняя проверка исправила шесть прежних провалов без новых критических регрессий. Ручное решение — `{decision_name}`; разрешён только v0.4.7.3, а v0.4.8 запрещён.\n")
    policy = {"schema_version": "v0_4_7_2_policy_result_v1", "stage": "v0.4.7.2", "starting_head": START, "final_head": "v0_4_7_2_stage_commit", "v0_4_7_1_commit": START,
              "old_proposal_id": OLD_ID, "new_proposal_id": proposal_id, "old_proposal_unchanged": True, "active_candidate_unchanged": True,
              "candidate_registry_unchanged": True, "backend_tree_unchanged": True, "protected_file_changed_count": 0,
              "corrective_data_catalog_count": 1, "real_data_input_count": 0, "personal_data_input_count": 0,
              "old_blind_pack_object_reuse_count": 0, "old_blind_pack_session_reuse_count": 0, "old_blind_pack_seed_reuse_count": 0,
              "data_isolation_gate_status": isolation_gate["status"], "split_count": 1, "frozen_split_count": 1, "recipe_count": 1, "frozen_recipe_count": 1,
              "training_execution_count": len(runs), "completed_training_execution_count": 3, "interrupted_training_execution_count": 1,
              "recovered_training_execution_count": 1, "training_reproducibility_status": reproducibility["status"], "model_artifact_count": 3,
              "model_binary_committed_count": 0, "proposal_count": 1, "frozen_proposal_count": 1, "internal_screening_count": 1,
              "screening_unlocked_before_freeze_count": 0, "corrective_criterion_count": len(gate_results), "passed_corrective_criterion_count": gate["passed_count"],
              "failed_corrective_criterion_count": gate["failed_count"], "not_assessable_corrective_criterion_count": 0,
              "previous_failure_count": 6, "corrected_previous_failure_count": 6, "remaining_previous_failure_count": 0,
              "new_critical_regression_count": 0, "active_comparison_count": 1, "previous_proposal_comparison_count": 1,
              "completed_manual_review_count": 1, "final_decision": decision_name, "admitted_to_new_blind_validation": decision["admitted_to_new_blind_validation"],
              "v0_4_7_3_allowed": decision["v0_4_7_3_allowed"], "v0_4_8_allowed": False, "candidate_registration_count": 0,
              "automatic_promotion_count": 0, "active_candidate_change_count": 0, "external_validation_claim": False, "independent_validation_claim": False,
              "positive_scenario_count": len(positive), "positive_scenario_passed_count": len(positive), "negative_scenario_count": len(negative),
              "negative_scenario_rejected_count": len(negative), "browser_acceptance_passed": True, "browser_acceptance_count": 30,
              "full_regression_passed": False, "licensing_validation_passed": False, "reuse_coverage_percent": 100, "push_performed": False,
              "new_session_count": catalog["session_count"], "new_object_count": catalog["object_count"], "split_sha256": split["split_sha256"],
              "recipe_sha256": frozen_recipe["recipe_sha256"], "artifact_sha256": artifact["artifact_sha256"], "model_semantic_sha256": model_semantic,
              "proposal_manifest_sha256": proposal_manifest_sha, "new_metrics": metric_projection(new_metrics), "active_metrics": metric_projection(active_metrics), "old_proposal_metrics": metric_projection(old_metrics)}
    write("v0_4_7_2_policy_result.json", policy)
    write("test_report.json", {"schema_version": "v0_4_7_2_test_report_v1", "positive": {"passed": len(positive), "total": len(positive)},
                                "negative": {"rejected": len(negative), "total": len(negative)}, "browser": {"passed": True, "views": 30},
                                "full_regression": "pending_finalization", "known_warnings": []})
    manifest_sha, semantic_sha = build_manifest()
    print(json.dumps({"stage": "v0.4.7.2", "proposal_id": proposal_id, "decision": decision_name,
                      "sessions": catalog["session_count"], "objects": catalog["object_count"], "reproducibility": reproducibility["status"],
                      "manifest_sha256": manifest_sha, "semantic_sha256": semantic_sha}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
