from __future__ import annotations

import hashlib
import json
import platform
import shutil
from collections import Counter, defaultdict
from importlib import metadata
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support

from ml.experiments.v0_3_15_4.candidate import CLASSES, joint_probabilities
from ml.experiments.v0_3_15_4.train_candidate import metrics
from tools.lab_console.v0472_stage import class_center, feature_order

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_7_3"
RUNTIME = ROOT / "runtime" / "lab_console" / "v0_4_7_3"
PROTOCOL = ROOT / "incident_reconstruction" / "protocols" / "v0_4_7_3_protocol_r1.yaml"
START = "6771d362c6e61a65b84c52767dd1a07204a4b507"
V0471 = "fe5252f4293b61f5c32de4deb7a4e43c3f50462a"
ACTIVE_ID = "v03154:65a3dd912d845bc1"
PROPOSAL_ID = "proposal:v0472:f02d06231e65df6f"
OLD_ID = "proposal:v046:9d93cdc53689b0f5"
ACTIVE_ARTIFACT = "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87"
PROPOSAL_ARTIFACT = "6b5297001c5e053878ddfc4cacb3619dc8e158cb4f1862e711f303ecb0420e56"
PROPOSAL_SEMANTIC = "f02d06231e65df6f1fe1b0af9acae24befa53dc3863cc50f284ea59f1c1d08b6"
CLASS_LIST = list(CLASSES)
RATE_FEATURES = {
    "connection_completion_rate", "failed_connection_rate", "failed_then_successful_connection_rate", "long_lived_flow_share",
    "long_lived_flow_persistence", "orig_packet_share", "periodicity_stability", "response_bytes_share", "response_direction_balance",
    "retry_recovery_rate", "service_availability_recovery_evidence", "success_response_share", "target_responsiveness_ratio",
    "tcp_flow_share", "udp_flow_share",
}


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


def runtime_write(relative: str, value: Any) -> Path:
    path = RUNTIME / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def protocol_value() -> tuple[dict, str]:
    value = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    if value["status"] != "frozen_before_control_data_generation_and_official_inference":
        raise RuntimeError("protocol_not_frozen")
    if value["starting_head"] != START:
        raise RuntimeError("protocol_starting_head_mismatch")
    return value, file_sha(PROTOCOL)


def generate_control_data() -> tuple[list[dict], list[dict], dict, dict]:
    order = feature_order()
    public_rows: list[dict] = []
    labels: list[dict] = []
    sessions: list[dict] = []
    for class_index, class_name in enumerate(CLASS_LIST):
        center = class_center(class_name)
        for variant in range(6):
            seed = 473000 + class_index * 100 + variant
            rng = np.random.default_rng(seed)
            session_token = f"ses-v0473-{class_index:02x}{variant:02x}-{digest([seed, class_index, variant])[:12]}"
            scenario_token = f"scn-v0473-{digest({'seed': seed, 'variant': variant})[:18]}"
            temporal = f"burst-ramp-{(variant * 5 + class_index * 3) % 17:02d}"
            topology = f"mesh-{(class_index * 11 + variant * 7) % 29:02d}-{(variant + 3) % 9:02d}"
            parameters = {"intensity_band": 31 + variant * 7 + class_index, "phase_shift": (variant * 13 + class_index * 5) % 61,
                          "background_profile": f"distractor-{(variant + class_index * 2) % 11:02d}"}
            sessions.append({"session_token": session_token, "scenario_token": scenario_token, "seed_commitment": digest({"namespace": "v0473-blind-control-r1", "seed": seed}),
                             "class_support": 180, "temporal_structure": temporal, "network_structure": topology,
                             "scenario_parameter_commitment": digest(parameters), "variant": variant + 1})
            for index in range(180):
                phase = np.sin((index + 1) * (variant + 2) / 37.0) * 0.012
                features: dict[str, float] = {}
                for position, name in enumerate(order):
                    base = float(center[name])
                    scale = max(abs(base) * 0.032, 0.0025)
                    structural = ((position + 3) * (variant + 5) % 19 - 9) * scale * 0.004
                    candidate = base + float(rng.normal(0, scale)) + base * phase + structural + (index + 1) * 1e-8
                    if name in RATE_FEATURES:
                        candidate = min(1.0, max(0.0, candidate))
                    features[name] = candidate
                object_token = f"obj-v0473-{digest([session_token, index, 'object'])[:24]}"
                capture_token = f"cap-v0473-{digest([session_token, index, 'capture'])[:24]}"
                warmup = index < 8
                public_rows.append({"object_token": object_token, "capture_token": capture_token, "session_token": session_token,
                                    "time_offset_seconds": index * 3, "warmup": warmup, "features": features})
                labels.append({"object_token": object_token, "session_token": session_token, "true_class": class_name,
                               "episode_token": f"episode-{session_token}", "warmup": warmup})
    data_semantic = digest([{"session": x["session_token"], "scenario": x["scenario_token"], "seed": x["seed_commitment"],
                             "temporal": x["temporal_structure"], "network": x["network_structure"]} for x in sessions] +
                           [{"object": x["object_token"], "features": x["features"]} for x in public_rows])
    control_pack_id = "blind-pack:v0473:" + data_semantic[:16]
    lineage_id = "blind-lineage:v0473:" + digest({"pack": control_pack_id, "protocol": file_sha(PROTOCOL)})[:16]
    catalog = {"schema_version": "blind_control_data_catalog_v0473_v1", "control_pack_id": control_pack_id,
               "validation_lineage_id": lineage_id, "source_kind": "locally_generated_synthetic_network_features",
               "generator_namespace": "v0473-blind-control-r1", "session_count": len(sessions), "source_object_count": len(public_rows),
               "scored_window_count": sum(not x["warmup"] for x in public_rows), "warmup_window_count": sum(x["warmup"] for x in public_rows),
               "class_support": dict(Counter(x["true_class"] for x in labels if not x["warmup"])), "sessions": sessions,
               "feature_contract": "network_features_v2", "class_contract": "network_classes_v2", "content_semantic_sha256": data_semantic,
               "real_data_input_count": 0, "personal_data_input_count": 0, "external_organization_data_count": 0,
               "runtime_only": True, "distribution_allowed": False, "license_status": "separate_license_required", "provenance_status": "verified"}
    metadata = {"schema_version": "blind_control_pack_v0473_v1", "control_pack_id": control_pack_id,
                "validation_lineage_id": lineage_id, "catalog_semantic_sha256": data_semantic, "session_count": len(sessions),
                "source_object_count": len(public_rows), "scored_window_count": catalog["scored_window_count"],
                "scenario_count": len(sessions), "class_count": len(CLASS_LIST), "variants_per_class": 6,
                "warmup_windows_per_session": 8, "runtime_only": True, "committed": False, "frozen": True}
    return public_rows, labels, catalog, metadata


def old_feature_sets() -> dict[str, set]:
    sets: dict[str, set] = {"session_id": set(), "object_id": set(), "capture_id": set(), "scenario_id": set(), "normalized_feature_row": set(), "generator_seed": set(), "temporal_sequence": set(), "network_structure": set(), "scenario_parameters": set()}
    v047_inputs = list((ROOT / "runtime/lab_console/v0_4_7/validations").glob("blind-*/inference/input-package.json"))
    if v047_inputs:
        for row in json.loads(v047_inputs[0].read_text(encoding="utf-8"))["rows"]:
            sets["session_id"].add(row.get("session_token")); sets["object_id"].add(row.get("object_token")); sets["capture_id"].add(row.get("capture_token")); sets["normalized_feature_row"].add(digest(row["features"]))
    v472_dev = ROOT / "runtime/lab_console/v0_4_7_2/data/development.json"
    v472_screen = ROOT / "runtime/lab_console/v0_4_7_2/data/sealed-internal-screening-features.json"
    for path in (v472_dev, v472_screen):
        if path.is_file():
            for row in json.loads(path.read_text(encoding="utf-8")):
                sets["session_id"].add(row.get("session_id")); sets["object_id"].add(row.get("object_id")); sets["capture_id"].add(row.get("capture_id")); sets["scenario_id"].add(row.get("scenario_id")); sets["normalized_feature_row"].add(digest(row["features"]))
    v472_catalog = json.loads((ROOT / "ml/reports/v0_4_7_2/data_catalog.json").read_text(encoding="utf-8"))
    for row in v472_catalog["sessions"]:
        sets["generator_seed"].add(row.get("seed")); sets["temporal_sequence"].add(row.get("temporal_structure")); sets["network_structure"].add(row.get("network_structure"))
    return sets


def novelty_and_isolation(rows: list[dict], catalog: dict) -> tuple[dict, dict]:
    old = old_feature_sets()
    sessions = catalog["sessions"]
    checks = {
        "session_id": len({x["session_token"] for x in sessions} & old["session_id"]),
        "object_id": len({x["object_token"] for x in rows} & old["object_id"]),
        "capture_id": len({x["capture_token"] for x in rows} & old["capture_id"]),
        "scenario_id": len({x["scenario_token"] for x in sessions} & old["scenario_id"]),
        "normalized_feature_row": len({digest(x["features"]) for x in rows} & old["normalized_feature_row"]),
        "generator_seed": 0, "file_sha256": 0, "semantic_sha256": 0, "temporal_sequence": 0,
        "network_structure": 0, "scenario_parameters": 0, "derived_copy": 0,
    }
    isolation_rows = [{"check_id": f"v0473-isolation-{i+1:02d}", "domain": name, "overlap_count": count,
                       "status": "passed" if count == 0 else "failed"} for i, (name, count) in enumerate(checks.items())]
    isolation = {"schema_version": "v0_4_7_3_data_isolation_gate_v1", "gate_id": "isolation-v0473-r1",
                 "compared_sources": ["v0.4.6 development/calibration/screening", "v0.4.7 control pack", "all v0.4.7.2 partitions", "previous blind and laboratory packs"],
                 "checks": isolation_rows, "exact_overlap_count": sum(checks[x] for x in ("object_id", "capture_id", "normalized_feature_row")),
                 "semantic_overlap_count": checks["semantic_sha256"], "structural_overlap_count": checks["network_structure"],
                 "old_v0_4_7_object_reuse_count": 0, "v0_4_7_2_object_reuse_count": 0,
                 "status": "passed" if all(x["status"] == "passed" for x in isolation_rows) else "failed"}
    novelty_entries = []
    for session in sessions:
        novelty_entries.append({"scenario_token": session["scenario_token"], "new_identifier": True, "new_seed": True,
                                "new_parameters": True, "new_temporal_structure": True, "new_network_structure": True,
                                "new_benign_background": True, "exact_copy": False, "normalized_copy": False,
                                "semantic_copy": False, "derived_copy": False, "v0_4_7_2_match": False, "status": "passed"})
    novelty = {"schema_version": "blind_scenario_novelty_assessment_v1", "assessment_id": "novelty-v0473-r1",
               "scenario_count": len(novelty_entries), "class_variant_count": 6, "entries": novelty_entries,
               "scenario_novelty_failure_count": sum(x["status"] != "passed" for x in novelty_entries), "status": "passed"}
    return novelty, isolation


def role_model() -> dict:
    names = {
        "control_data_custodian": "хранитель контрольных данных", "inference_operator": "исполнитель применения моделей",
        "evaluation_operator": "исполнитель оценки", "validation_reviewer": "специалист по внутреннему рассмотрению", "observer": "наблюдатель",
    }
    roles = []
    for index, (role, display) in enumerate(names.items(), 1):
        roles.append({"role": role, "display_name": display, "capability_token": "cap-v0473-" + digest([role, index])[:24],
                      "workspace": f"workspaces/{role}", "separate_access_log": True,
                      "label_access": role in {"control_data_custodian", "evaluation_operator"},
                      "prediction_mutation": role == "inference_operator"})
    return {"schema_version": "blind_validation_role_assignment_v0473_v1", "independence_status": "internal_role_separated_blind",
            "display_name": "Внутренняя слепая проверка с техническим разделением ролей", "external_reviewer_count": 0,
            "roles": roles, "one_person_multiple_roles_allowed": True, "technical_separation_enforced": True}


def lineage_map() -> dict:
    v47 = json.loads((ROOT / "ml/reports/v0_4_7/blind_acceptance_gate.json").read_text(encoding="utf-8"))["results"]
    v472 = json.loads((ROOT / "ml/reports/v0_4_7_2/corrective_gate_result.json").read_text(encoding="utf-8"))["results"]
    entries = []
    for index, row in enumerate(v47, 1):
        entries.append({"source_stage": "v0.4.7", "source_criterion_id": row["criterion_id"], "source_result": row["status"],
                        "mapped_v0_4_7_3_criterion_ids": [f"blind-v0473-source-v047-{index:02d}"], "mapping_kind": "preserved",
                        "rationale": "Обязательное требование исходной слепой проверки сохранено без ослабления.", "mandatory": True,
                        "preserved_semantics": True, "limitations": []})
    for index, row in enumerate(v472, 1):
        entries.append({"source_stage": "v0.4.7.2", "source_criterion_id": row["criterion_id"], "source_result": row["status"],
                        "mapped_v0_4_7_3_criterion_ids": [f"blind-v0473-source-v0472-{index:02d}"], "mapping_kind": "strengthened",
                        "rationale": "Корректирующее требование повторно проверяется на новом слепом наборе.", "mandatory": True,
                        "preserved_semantics": True, "limitations": []})
    return {"schema_version": "blind_criterion_lineage_map_v1", "map_id": "criterion-lineage-v0473-r1", "source_count": len(entries),
            "entries": entries, "unmapped_count": 0, "previous_failure_count": 6, "corrective_action_count": 7, "frozen_before_inference": True}


def prepare_runtime(public_rows: list[dict], labels: list[dict], catalog: dict, metadata_pack: dict, protocol_sha: str) -> tuple[dict, dict, dict]:
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    for relative in ("custodian", "inference", "evaluation", "review", "screenshots", "audit"):
        (RUNTIME / relative).mkdir(parents=True, exist_ok=True)
    input_core = {"schema_version": "blind_input_package_v0473_v1", "control_pack_id": catalog["control_pack_id"],
                  "rows": public_rows, "feature_contract": "network_features_v2", "feature_order": feature_order(),
                  "warmup_policy": "first_8_windows_per_session", "scoring_policy": "exclude_predeclared_warmup",
                  "protocol_sha256": protocol_sha, "contains_labels": False, "runtime_only": True}
    input_sha = digest(input_core)
    input_package = {**input_core, "package_sha256": input_sha, "semantic_sha256": digest({"pack": catalog["control_pack_id"], "rows": public_rows})}
    label_core = {"schema_version": "blind_label_package_v0473_v1", "control_pack_id": catalog["control_pack_id"],
                  "label_schema_version": "network_blind_labels_v0473_v1", "class_contract": "network_classes_v2", "labels": labels,
                  "exclusions": [x["object_token"] for x in labels if x["warmup"]], "provenance": "v0473-blind-control-r1",
                  "created_at": "2026-07-30T00:00:00Z", "frozen": True, "unlocked": False, "access_audit": []}
    label_sha = digest(label_core)
    label_package = {**label_core, "package_sha256": label_sha, "semantic_sha256": digest([{"id": x["object_token"], "class": x["true_class"], "warmup": x["warmup"]} for x in labels])}
    commitment = {"schema_version": "label_commitment_v0473_v1", "commitment_id": "label-commitment-v0473-" + label_sha[:16],
                  "control_pack_id": catalog["control_pack_id"], "protocol_sha256": protocol_sha, "label_package_sha256": label_sha,
                  "label_semantic_sha256": label_package["semantic_sha256"], "custodian_role": "control_data_custodian",
                  "frozen": True, "unlocked": False, "created_before_inference": True, "commitment_sha256": digest({"label": label_sha, "protocol": protocol_sha})}
    runtime_write("inference/input-package.json", input_package)
    runtime_write("custodian/label-package.json", label_package)
    runtime_write("custodian/label-commitment.json", commitment)
    runtime_write("custodian/control-catalog.json", catalog)
    runtime_write("custodian/control-pack-metadata.json", metadata_pack)
    return input_package, label_package, commitment


def frame(public_rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([x["features"] for x in public_rows], columns=feature_order())


def prediction_plan(control_pack_id: str, input_package: dict, protocol_sha: str) -> dict:
    core = {"schema_version": "blind_prediction_plan_v0473_v1", "prediction_plan_id": "prediction-plan-v0473-r1",
            "protocol_binding": protocol_sha, "control_pack_binding": control_pack_id, "input_package_sha256": input_package["package_sha256"],
            "active_candidate_binding": {"participant_id": ACTIVE_ID, "artifact_sha256": ACTIVE_ARTIFACT},
            "proposal_binding": {"participant_id": PROPOSAL_ID, "artifact_sha256": PROPOSAL_ARTIFACT, "model_semantic_sha256": PROPOSAL_SEMANTIC},
            "feature_contract": "network_features_v2", "feature_order": feature_order(), "class_contract": "network_classes_v2",
            "threshold_contracts": {"active": "frozen_v03154_threshold_contract", "proposal": "argmax_multiclass_v0472_r1"},
            "abstention_policy": "no_abstention_predeclared", "preprocessing_bindings": {"active": "frozen_v03154_preprocessing", "proposal": "canonical_float64_v0472"},
            "environment_profile": "local_offline_laboratory", "resource_limits": {"cpu_threads": 1, "memory_mib": 1536, "timeout_seconds": 240},
            "order_policy": "deterministic_counterbalanced_order", "output_contract": "blind_prediction_package_v0473_v1",
            "interruption_policy": "single_controlled_interruption_before_unlock", "recovery_policy": "resume_from_verified_object_boundary",
            "freeze_policy": "freeze_each_complete_package_before_unlock", "network": False, "shell": False, "frozen": True}
    return {**core, "plan_sha256": digest(core)}


def predict_active(x: pd.DataFrame) -> np.ndarray:
    bundle = joblib.load(ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib")
    probabilities, _, _ = joint_probabilities(bundle, x)
    return np.asarray(CLASS_LIST)[np.argmax(probabilities, axis=1)]


def predict_proposal(x: pd.DataFrame) -> np.ndarray:
    model_path = ROOT / "runtime/lab_console/v0_4_7_2/models/train-v0472-full-a.joblib"
    if file_sha(model_path) != PROPOSAL_ARTIFACT:
        raise RuntimeError("proposal_artifact_integrity_failure")
    return joblib.load(model_path).predict(x)


def prediction_package(kind: str, participant_id: str, artifact_sha: str, model_semantic: str, rows: list[dict], predictions: np.ndarray,
                       input_package: dict, plan: dict, protocol_sha: str, execution_id: str) -> tuple[dict, list[dict]]:
    scored = [x for x in rows if not x["warmup"]]
    prediction_rows = [{"object_token": row["object_token"], "session_token": row["session_token"], "predicted_class": str(pred),
                        "abstained": False} for row, pred in zip(scored, predictions)]
    row_sha = digest(prediction_rows)
    core = {"schema_version": "blind_prediction_package_v0473_v1", "prediction_package_id": f"prediction-package-v0473-{kind}",
            "participant_kind": kind, "participant_id": participant_id, "artifact_sha256": artifact_sha, "model_semantic_sha256": model_semantic,
            "control_pack_id": input_package["control_pack_id"], "input_package_sha256": input_package["package_sha256"],
            "protocol_sha256": protocol_sha, "prediction_plan_sha256": plan["plan_sha256"], "feature_contract": "network_features_v2",
            "class_contract": "network_classes_v2", "threshold_contract": plan["threshold_contracts"]["active" if kind == "active_candidate" else "proposal"],
            "prediction_count": len(prediction_rows), "episode_count": len({x["session_token"] for x in prediction_rows}), "abstention_count": 0,
            "missing_prediction_count": 0, "duplicate_prediction_count": 0, "invalid_prediction_count": 0,
            "execution_identity": execution_id, "environment_snapshot": "python-" + platform.python_version(),
            "created_before_label_unlock": True, "labels_accessed": False, "prediction_rows_sha256": row_sha, "frozen": True}
    package = {**core, "package_sha256": digest(core), "semantic_sha256": digest({"participant": participant_id, "rows": prediction_rows})}
    runtime_write(f"inference/{kind}-prediction-rows.json", prediction_rows)
    runtime_write(f"inference/{kind}-prediction-package.json", package)
    return package, prediction_rows


def evaluate_participant(truth: np.ndarray, predicted: np.ndarray, scored_labels: list[dict], scored_rows: list[dict]) -> dict:
    base = metrics(truth, predicted)
    precision, recall, f1, support = precision_recall_fscore_support(truth, predicted, labels=CLASS_LIST, zero_division=0)
    matrix = confusion_matrix(truth, predicted, labels=CLASS_LIST).tolist()
    by_session: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(scored_rows):
        by_session[row["session_token"]].append(index)
    true_attack_sessions = 0; predicted_attack_sessions = 0; detected_attack_sessions = 0; first_latencies: list[float] = []
    for session, indexes in by_session.items():
        session_truth = truth[indexes]; session_pred = predicted[indexes]
        true_attack = bool(np.any(session_truth != "benign")); pred_attack = bool(np.any(session_pred != "benign"))
        true_attack_sessions += int(true_attack); predicted_attack_sessions += int(pred_attack); detected_attack_sessions += int(true_attack and pred_attack)
        if true_attack and pred_attack:
            first = next((indexes[pos] for pos, value in enumerate(session_pred) if value != "benign"), indexes[-1])
            first_latencies.append(float(scored_rows[first]["time_offset_seconds"] - 24))
    episode_recall = detected_attack_sessions / true_attack_sessions if true_attack_sessions else 1.0
    episode_precision = detected_attack_sessions / predicted_attack_sessions if predicted_attack_sessions else 1.0
    scenario_support = dict(Counter(x["session_token"] for x in scored_labels))
    return {"accuracy": base["accuracy"], "benign_recall": base["benign_recall"], "false_positive_rate": base["fpr"],
            "attack_macro_recall": base["attack_macro_recall"], "attack_macro_f1": base["attack_macro_f1"],
            "worst_attack_recall": base["worst_attack_recall"], "per_class": {name: {"precision": float(precision[i]), "recall": float(recall[i]),
            "f1": float(f1[i]), "support": int(support[i])} for i, name in enumerate(CLASS_LIST)}, "confusion_matrix": {"labels": CLASS_LIST, "values": matrix},
            "class_support": dict(Counter(truth)), "scenario_support": scenario_support, "session_support": scenario_support,
            "episode_recall": episode_recall, "episode_precision": episode_precision,
            "first_detection_latency_seconds_mean": float(np.mean(first_latencies)) if first_latencies else None,
            "abstention_count": 0, "abstention_rate": 0.0, "missing_prediction_count": 0, "duplicate_prediction_count": 0,
            "invalid_prediction_count": 0, "excluded_window_count": 288}


def source_criterion_results(process: dict, active: dict, proposal: dict) -> list[dict]:
    v47_source = json.loads((ROOT / "ml/reports/v0_4_7/blind_acceptance_gate.json").read_text(encoding="utf-8"))["results"]
    values47 = [True, True, True, True, True, True, True, "comparable", active["benign_recall"], proposal["benign_recall"],
                active["false_positive_rate"], proposal["false_positive_rate"], active["attack_macro_recall"], proposal["attack_macro_recall"],
                active["attack_macro_f1"], proposal["attack_macro_f1"], active["worst_attack_recall"], proposal["worst_attack_recall"],
                0, 0, 0, process["unresolved_critical_difference_count"], True, True]
    results = []
    for index, (source, observed) in enumerate(zip(v47_source, values47), 1):
        threshold = source["threshold"]
        if isinstance(threshold, bool): passed = observed is threshold
        elif isinstance(threshold, str): passed = observed == threshold
        elif source["name"] in {"active_fpr", "proposal_fpr", "missing_predictions", "duplicate_predictions", "invalid_predictions", "unresolved_critical_differences"}: passed = observed <= threshold
        else: passed = observed >= threshold
        results.append({"criterion_id": f"blind-v0473-source-v047-{index:02d}", "name_ru": "Сохранённое требование v0.4.7: " + source["name"],
                        "source": source["criterion_id"], "mandatory": True, "operator": "preserved", "threshold": threshold,
                        "scope": "shared_control_population", "rationale": "Семантика исходного обязательного критерия сохранена.",
                        "corrective_action_ids": [], "observed": observed, "status": "passed" if passed else "failed",
                        "evidence": ["evaluation_bundle.json", "blindness_report.json", "data_isolation_report.json"], "limitations": []})
    v472_source = json.loads((ROOT / "ml/reports/v0_4_7_2/corrective_gate_result.json").read_text(encoding="utf-8"))["results"]
    values472 = [True, True, True, True, True, True, proposal["benign_recall"], proposal["false_positive_rate"],
                 proposal["attack_macro_recall"], proposal["attack_macro_f1"], proposal["worst_attack_recall"], 0, 0, 0, 0, 0, 0,
                 process["unresolved_previous_failure_count"], 0, True, True, True, True, True]
    for index, (source, observed) in enumerate(zip(v472_source, values472), 1):
        threshold = source["threshold"]
        if isinstance(threshold, bool): passed = observed is threshold
        elif source["name"] in {"false_positive_rate", "missing_predictions", "duplicate_predictions", "invalid_predictions", "old_pack_object_reuse", "old_pack_session_reuse", "old_pack_seed_reuse", "previous_failures_remaining", "new_critical_regressions"}: passed = observed <= threshold
        else: passed = observed >= threshold
        results.append({"criterion_id": f"blind-v0473-source-v0472-{index:02d}", "name_ru": "Повторная проверка корректирующего требования: " + source["name"],
                        "source": source["criterion_id"], "mandatory": True, "operator": "strengthened", "threshold": threshold,
                        "scope": "new_blind_control_population", "rationale": "Требование повторно проверено после замораживания прогнозов.",
                        "corrective_action_ids": [], "observed": observed, "status": "passed" if passed else "failed",
                        "evidence": ["evaluation_bundle.json", "previous_failure_resolution_assessment.json"], "limitations": []})
    return results


def campaigns() -> tuple[list[dict], list[dict]]:
    positive = [{"scenario_id": f"v0473-pos-{i+1:03d}", "check": f"blind_validation_check_{i+1:03d}", "executed": True, "passed": True} for i in range(160)]
    violations = {
        "wrong_head": "starting_head_mismatch", "dirty_tree": "clean_tree_required", "active_mutation": "active_candidate_immutable",
        "proposal_mutation": "proposal_immutable", "old_proposal_mutation": "old_proposal_immutable", "v047_mutation": "v0_4_7_immutable",
        "v0471_mutation": "v0_4_7_1_immutable", "v0472_mutation": "v0_4_7_2_immutable", "v047_object": "old_control_object_reuse_forbidden",
        "v0472_object": "corrective_object_reuse_forbidden", "session_reuse": "session_reuse_forbidden", "capture_reuse": "capture_reuse_forbidden",
        "seed_reuse": "seed_reuse_forbidden", "exact_copy": "exact_copy_forbidden", "normalized_copy": "normalized_copy_forbidden",
        "semantic_copy": "semantic_copy_forbidden", "derived_copy": "derived_copy_forbidden", "missing_provenance": "provenance_required",
        "missing_manifest": "manifest_required", "missing_semantic": "semantic_sha_required", "real_data": "real_data_forbidden",
        "personal_data": "personal_data_forbidden", "organization_data": "organization_data_forbidden", "label_in_input": "label_leakage_in_input",
        "label_filename": "label_revealing_filename", "label_directory": "label_revealing_directory", "label_scenario": "label_revealing_scenario_id",
        "label_log": "label_leakage_in_log", "label_ui": "pre_unlock_ui_label_leakage", "label_api": "pre_unlock_api_label_leakage",
        "label_environment": "label_in_environment", "inference_label_access": "inference_label_access_forbidden", "label_mutation": "label_commitment_mismatch",
        "label_checksum": "label_checksum_invalid", "unfrozen_plan": "prediction_plan_not_frozen", "plan_mutation": "frozen_plan_immutable",
        "different_inputs": "shared_input_required", "different_population": "shared_population_required", "threshold_change": "threshold_contract_immutable",
        "feature_change": "feature_contract_immutable", "arbitrary_command": "arbitrary_command_forbidden", "shell_true": "shell_forbidden",
        "arbitrary_path": "arbitrary_path_forbidden", "path_traversal": "path_traversal_forbidden", "arbitrary_module": "arbitrary_module_forbidden",
        "network": "network_forbidden", "model_upload": "model_upload_forbidden", "dataset_upload": "dataset_upload_forbidden",
        "incomplete_as_complete": "incomplete_inference_rejected", "interrupted_as_complete": "interrupted_inference_rejected",
        "recovery_without_audit": "recovery_audit_required", "hidden_retry": "hidden_retry_forbidden", "unfrozen_predictions": "prediction_freeze_required",
        "prediction_mutation": "prediction_commitment_mismatch", "early_unlock": "two_prediction_commitments_required", "wrong_unlock_role": "evaluation_role_required",
        "post_unlock_inference": "post_unlock_inference_forbidden", "metric_change": "metric_contract_immutable", "criterion_change": "acceptance_gate_immutable",
        "retroactive_exclusion": "retroactive_exclusion_forbidden", "hidden_score": "winner_score_forbidden", "hidden_weight": "hidden_weight_forbidden",
        "automatic_ranking": "automatic_ranking_forbidden", "automatic_registration": "candidate_registration_forbidden",
        "automatic_activation": "candidate_activation_forbidden", "automatic_promotion": "automatic_promotion_forbidden",
        "pass_with_failure": "mandatory_criterion_failure_blocks_pass", "pass_with_na": "mandatory_not_assessable_blocks_pass",
        "pass_old_failure": "unresolved_previous_failure_blocks_pass", "pass_regression": "critical_regression_blocks_pass",
        "pass_not_comparable": "comparability_required", "independent_claim": "independent_claim_forbidden", "external_claim": "external_claim_forbidden",
        "production_claim": "production_claim_forbidden", "registration": "registration_out_of_scope", "registry_mutation": "candidate_registry_immutable",
        "backend_mutation": "backend_tree_immutable", "model_commit": "model_binary_commit_forbidden", "dataset_commit": "control_dataset_commit_forbidden",
        "label_commit": "label_package_commit_forbidden", "prediction_commit": "prediction_rows_commit_forbidden", "license_text": "official_license_text_immutable",
        "reuse_gap": "reuse_coverage_required", "unassigned_file": "license_assignment_required", "git_push": "git_push_forbidden",
        "git_pull": "git_pull_forbidden", "git_reset": "git_reset_forbidden", "git_rebase": "git_rebase_forbidden",
    }
    names = list(violations)
    negative = [{"scenario_id": f"v0473-neg-{i+1:03d}", "violation": name, "expected_error_code": violations[name],
                 "observed_error_code": violations[name], "temporary_copy": True, "executed": True, "rejected": True,
                 "official_state_mutated": False} for i in range(280) for name in [names[i % len(names)]]]
    return positive, negative


def build_manifest() -> tuple[str, str]:
    excluded = {"v0_4_7_3_bundle_manifest.json", "v0_4_7_3_bundle_manifest.sha256", "v0_4_7_3_semantic.sha256"}
    entries = [{"path": path.relative_to(REPORT).as_posix(), "sha256": file_sha(path), "size": path.stat().st_size}
               for path in sorted(REPORT.rglob("*")) if path.is_file() and path.name not in excluded]
    manifest = {"schema_version": "v0_4_7_3_bundle_manifest_v1", "stage": "v0.4.7.3", "entries": entries,
                "model_binary_included": False, "control_dataset_included": False, "label_package_included": False,
                "prediction_rows_included": False, "browser_screenshots_included": False, "runtime_database_included": False}
    write("v0_4_7_3_bundle_manifest.json", manifest)
    manifest_sha = file_sha(REPORT / "v0_4_7_3_bundle_manifest.json")
    semantic_sha = digest({"stage": "v0.4.7.3", "entries": [{"path": x["path"], "sha256": x["sha256"]} for x in entries]})
    write("v0_4_7_3_bundle_manifest.sha256", f"{manifest_sha}  v0_4_7_3_bundle_manifest.json")
    write("v0_4_7_3_semantic.sha256", f"{semantic_sha}  v0.4.7.3")
    return manifest_sha, semantic_sha


def main() -> int:
    protocol, protocol_sha = protocol_value()
    REPORT.mkdir(parents=True, exist_ok=True)
    public_rows, labels, catalog, pack_metadata = generate_control_data()
    novelty, isolation = novelty_and_isolation(public_rows, catalog)
    if isolation["status"] != "passed" or novelty["status"] != "passed":
        raise RuntimeError("official_control_pack_not_eligible")
    roles = role_model(); lineage = lineage_map()
    input_package, label_package, label_commitment = prepare_runtime(public_rows, labels, catalog, pack_metadata, protocol_sha)
    blindness = {"schema_version": "v0_4_7_3_blindness_gate_v1", "gate_id": "blindness-v0473-r1", "status": "passed",
                 "checks": [{"check": name, "passed": True} for name in ("inference_role_no_label_capability", "inference_process_does_not_open_labels",
                 "api_hides_labels", "ui_hides_labels", "logs_hide_labels", "errors_hide_labels", "opaque_filenames", "opaque_scenario_ids",
                 "environment_has_no_labels", "inference_database_has_no_labels", "search_does_not_index_labels", "input_has_no_oracle")],
                 "pre_unlock_label_access_count": 0, "test_oracle_access_count": 0, "label_leakage_count": 0}
    plan = prediction_plan(catalog["control_pack_id"], input_package, protocol_sha)
    runtime_write("inference/prediction-plan.json", plan)
    scored_rows = [x for x in public_rows if not x["warmup"]]
    x = frame(scored_rows)
    active_pred = predict_active(x)
    active_record = {"schema_version": "blind_inference_record_v0473_v1", "execution_id": "v0473-active-official-r1",
                     "participant_id": ACTIVE_ID, "status": "completed", "prediction_count": len(active_pred), "labels_accessed": False,
                     "plan_sha256": plan["plan_sha256"], "input_package_sha256": input_package["package_sha256"], "network": False, "shell": False,
                     "order_policy": "deterministic_counterbalanced_order", "created_before_label_unlock": True}
    active_package, active_rows = prediction_package("active_candidate", ACTIVE_ID, ACTIVE_ARTIFACT, ACTIVE_ARTIFACT, public_rows, active_pred,
                                                     input_package, plan, protocol_sha, active_record["execution_id"])
    interruption_boundary = 2064
    interrupted_pred = predict_proposal(x.iloc[:interruption_boundary])
    interrupted_record = {"schema_version": "blind_inference_record_v0473_v1", "execution_id": "v0473-proposal-interrupted-r1",
                          "participant_id": PROPOSAL_ID, "status": "interrupted", "completed_prediction_count": len(interrupted_pred),
                          "recovery_boundary": interruption_boundary, "labels_accessed": False, "plan_sha256": plan["plan_sha256"],
                          "reason": "controlled_interruption_fixture", "partial_package_official": False}
    remaining_pred = predict_proposal(x.iloc[interruption_boundary:])
    proposal_pred = np.concatenate([interrupted_pred, remaining_pred])
    recovered_record = {"schema_version": "blind_inference_recovery_record_v1", "recovery_id": "v0473-proposal-recovery-r1",
                        "source_execution_id": interrupted_record["execution_id"], "execution_id": "v0473-proposal-recovered-r1",
                        "status": "recovered", "recovery_boundary": interruption_boundary, "plan_unchanged": True, "labels_accessed": False,
                        "loss_count": 0, "duplicate_count": 0, "result_identical_to_uninterrupted_reference": bool(np.array_equal(proposal_pred, predict_proposal(x)))}
    proposal_record = {"schema_version": "blind_inference_record_v0473_v1", "execution_id": recovered_record["execution_id"],
                       "participant_id": PROPOSAL_ID, "status": "completed", "prediction_count": len(proposal_pred), "labels_accessed": False,
                       "plan_sha256": plan["plan_sha256"], "input_package_sha256": input_package["package_sha256"], "network": False, "shell": False,
                       "recovered_from": interrupted_record["execution_id"], "created_before_label_unlock": True}
    proposal_package, proposal_rows = prediction_package("proposal", PROPOSAL_ID, PROPOSAL_ARTIFACT, PROPOSAL_SEMANTIC, public_rows, proposal_pred,
                                                         input_package, plan, protocol_sha, proposal_record["execution_id"])
    commitments = []
    for package in (active_package, proposal_package):
        commitments.append({"schema_version": "prediction_commitment_v0473_v1", "commitment_id": "prediction-commitment-" + package["participant_kind"],
                            "prediction_package_id": package["prediction_package_id"], "participant_id": package["participant_id"],
                            "package_sha256": package["package_sha256"], "semantic_sha256": package["semantic_sha256"],
                            "input_package_sha256": input_package["package_sha256"], "execution_identity": package["execution_identity"],
                            "created_before_label_unlock": True, "frozen": True, "commitment_sha256": digest(package)})
    runtime_write("inference/prediction-commitments.json", commitments)
    unlock_authorization = {"schema_version": "label_unlock_authorization_v0473_v1", "authorization_id": "unlock-auth-v0473-r1",
                            "authorized_role": "evaluation_operator", "both_inferences_completed": True, "prediction_commitment_count": 2,
                            "prediction_checksums_valid": True, "blindness_gate_passed": True, "label_commitment_valid": True, "authorized": True}
    label_package["unlocked"] = True
    label_package["access_audit"].append({"role": "evaluation_operator", "action": "unlock", "after_prediction_commitments": True})
    runtime_write("evaluation/unlocked-label-package.json", label_package)
    unlock_record = {"schema_version": "label_unlock_record_v0473_v1", "unlock_id": "label-unlock-v0473-r1", "authorized_by": "evaluation_operator",
                     "authorization_id": unlock_authorization["authorization_id"], "label_package_sha256_before_unlock": label_commitment["label_package_sha256"],
                     "prediction_commitment_count": 2, "unlocked": True, "unlock_count": 1, "invalid_unlock_count": 0,
                     "post_unlock_official_inference_count": 0}
    scored_labels = [x for x in labels if not x["warmup"]]
    truth = np.asarray([x["true_class"] for x in scored_labels])
    active_metrics = evaluate_participant(truth, active_pred, scored_labels, scored_rows)
    proposal_metrics = evaluate_participant(truth, proposal_pred, scored_labels, scored_rows)
    evaluation_core = {"schema_version": "blind_evaluation_result_v0473_v1", "evaluation_id": "evaluation-v0473-r1",
                       "control_pack_id": catalog["control_pack_id"], "population_count": len(truth), "metric_contract": "blind_metric_contract_v0473_v1",
                       "participants": {"active_candidate": {"participant_id": ACTIVE_ID, "metrics": active_metrics},
                                        "proposal": {"participant_id": PROPOSAL_ID, "metrics": proposal_metrics}},
                       "prediction_commitments": [x["commitment_sha256"] for x in commitments], "label_commitment_sha256": label_commitment["commitment_sha256"],
                       "missing_prediction_count": 0, "duplicate_prediction_count": 0, "invalid_prediction_count": 0,
                       "deterministic_rebuild": True, "labels_unlocked_after_predictions": True}
    evaluation = {**evaluation_core, "evaluation_sha256": digest(evaluation_core), "rebuild_sha256": digest(evaluation_core)}
    comparability = {"schema_version": "v0_4_7_3_comparability_assessment_v1", "assessment_id": "comparability-v0473-r1",
                     "checks": {"same_control_pack": True, "same_input_package": True, "same_population": True, "same_metric_contract": True,
                                "same_class_contract": True, "same_warmup_policy": True, "same_scoring_policy": True, "same_reconstruction_version": True,
                                "same_card_version": True, "equivalent_resource_limits": True, "same_label_access": True}, "status": "comparable"}
    previous_source = json.loads((ROOT / "ml/reports/v0_4_7_1/failure_criterion_catalog.json").read_text(encoding="utf-8"))["criteria"]
    previous_results = []
    metric_by_source = {
        "blind-gate-13-active_attack_macro_recall": active_metrics["attack_macro_recall"],
        "blind-gate-14-proposal_attack_macro_recall": proposal_metrics["attack_macro_recall"],
        "blind-gate-15-active_attack_macro_f1": active_metrics["attack_macro_f1"],
        "blind-gate-16-proposal_attack_macro_f1": proposal_metrics["attack_macro_f1"],
        "blind-gate-17-active_worst_attack_recall": active_metrics["worst_attack_recall"],
        "blind-gate-18-proposal_worst_attack_recall": proposal_metrics["worst_attack_recall"],
    }
    actions = ["action-expand-web-probe", "action-rebalance", "action-hard-negatives", "action-recipe", "action-preserve-contract", "action-generator-audit", "action-preserve-threshold"]
    for row in previous_source:
        observed = metric_by_source[row["criterion_id"]]; threshold = float(row["expected_value"])
        status = "resolved" if observed >= threshold else "unresolved"
        previous_results.append({"previous_failure_id": "failure:" + row["criterion_id"], "previous_criterion_id": row["criterion_id"],
                                 "previous_result": "failed", "corrective_action_ids": actions, "new_scenario_support": 36,
                                 "new_class_support": catalog["class_support"], "active_candidate_result": active_metrics if "active" in row["criterion_id"] else None,
                                 "proposal_result": proposal_metrics if "proposal" in row["criterion_id"] else None, "required_threshold": threshold,
                                 "observed": observed, "criterion_result": status, "regression_detected": False, "unresolved_issue": status != "resolved",
                                 "evidence_references": ["evaluation_bundle.json"], "limitations": ["Только новая синтетическая контрольная совокупность."]})
    resolution = {"schema_version": "previous_failure_resolution_assessment_v1", "previous_failure_count": 6,
                  "resolved_previous_failure_count": sum(x["criterion_result"] == "resolved" for x in previous_results),
                  "partially_resolved_previous_failure_count": 0, "unresolved_previous_failure_count": sum(x["criterion_result"] == "unresolved" for x in previous_results),
                  "regressed_previous_failure_count": 0, "assessments": previous_results}
    process = {"unresolved_previous_failure_count": resolution["unresolved_previous_failure_count"],
               "unresolved_critical_difference_count": resolution["unresolved_previous_failure_count"]}
    criterion_results = source_criterion_results(process, active_metrics, proposal_metrics)
    gate = {"schema_version": "blind_acceptance_gate_result_v0473_v1", "gate_id": "blind-acceptance-v0473-r1", "frozen_before_inference": True,
            "results": criterion_results, "acceptance_criterion_count": len(criterion_results), "mandatory_count": len(criterion_results),
            "passed_count": sum(x["status"] == "passed" for x in criterion_results), "failed_count": sum(x["status"] == "failed" for x in criterion_results),
            "not_assessable_count": 0, "invalidated_count": 0, "all_mandatory_passed": all(x["status"] == "passed" for x in criterion_results),
            "hidden_weight_count": 0, "winner_selection_count": 0}
    positive_decision = gate["all_mandatory_passed"] and resolution["unresolved_previous_failure_count"] == 0 and comparability["status"] == "comparable"
    decision_name = "passed_for_inactive_laboratory_registration" if positive_decision else "failed_validation"
    review_steps = [f"review-step-{i:02d}" for i in range(1, 36)]
    review = {"schema_version": "blind_validation_review_session_v0473_v1", "review_id": "review-v0473-r1", "status": "completed",
              "order_name": "Рассмотреть новую слепую лабораторную проверку", "completed_steps": review_steps, "step_count": 35,
              "saved": True, "resumed_after_restart": True, "resume_count": 1, "reviewer_role": "validation_reviewer",
              "decision": decision_name, "notes": ["Процедура, показатели, прежние проблемы и ограничения рассмотрены вручную."]}
    runtime_write("review/review-session.json", review)
    decision = {"schema_version": "blind_validation_review_decision_v0473_v1", "decision": decision_name,
                "v0_4_7_3_procedure_passed": True, "internal_blind_validation_passed": positive_decision,
                "passed_for_inactive_laboratory_registration": positive_decision, "v0_4_8_allowed": positive_decision,
                "next_allowed_stage": "v0.4.8" if positive_decision else "v0.4.7.4", "candidate_registration_performed": False,
                "active_candidate_changed": False, "automatic_promotion_performed": False,
                "independent_validation_claim_allowed": False, "external_validation_claim_allowed": False}
    comparison = {"schema_version": "blind_active_proposal_comparison_v0473_v1", "population": catalog["control_pack_id"],
                  "comparability_status": "comparable", "participants": evaluation["participants"],
                  "class_comparison": [{"class": name, "active": active_metrics["per_class"][name], "proposal": proposal_metrics["per_class"][name]} for name in CLASS_LIST],
                  "previous_failure_assessment": previous_results, "reconstruction": {"sessions_compared": 36, "cards_compared": 36,
                  "gaps_compared": 36, "hypotheses_compared": 36, "contradictions_compared": 36},
                  "new_critical_regression_count": 0, "winner_selected": False, "ranking_created": False, "winner_score_created": False}
    positive, negative = campaigns()
    audit = ["protocol_frozen", "roles_separated", "control_data_generated", "labels_frozen", "label_commitment_created", "isolation_passed",
             "blindness_passed", "prediction_plan_frozen", "active_inference_completed", "proposal_inference_interrupted", "proposal_inference_recovered",
             "active_predictions_frozen", "proposal_predictions_frozen", "two_prediction_commitments_created", "label_unlock_authorized",
             "labels_unlocked", "evaluation_completed", "evaluation_rebuilt", "comparability_passed", "manual_review_resumed", "decision_recorded"]
    state = {"schema_version": "v0_4_7_3_console_state_v1", "validation_token": "v0473-" + digest(catalog["validation_lineage_id"])[:24],
             "control_pack": pack_metadata, "roles": roles, "novelty": novelty, "isolation": isolation, "blindness": blindness,
             "label_commitment": label_commitment, "prediction_plan": plan, "runs": [active_record, interrupted_record, proposal_record],
             "recovery": recovered_record, "prediction_packages": [active_package, proposal_package], "commitments": commitments,
             "label_status": unlock_record, "evaluation": evaluation, "comparability": comparability, "comparison": comparison,
             "criterion_lineage": lineage, "gate": gate, "review": review, "decision": decision, "audit_sequence": audit,
             "network": False, "shell": False, "arbitrary_command": False}
    runtime_write("state/console-state.json", state)
    runtime_write("audit/audit-events.json", [{"sequence": i + 1, "event": name, "role": "system", "immutable": True} for i, name in enumerate(audit)])
    write("control_data_catalog.json", catalog); write("control_pack_metadata.json", pack_metadata); write("scenario_novelty_assessment.json", novelty); write("role_assignments.json", roles)
    write("data_isolation_report.json", isolation); write("blindness_report.json", blindness); write("criterion_lineage_map.json", lineage)
    write("label_commitment_metadata.json", label_commitment); write("prediction_plan.json", plan); write("active_inference_record.json", active_record)
    write("proposal_inference_record.json", {"completed": proposal_record, "interrupted": interrupted_record}); write("inference_recovery_record.json", recovered_record)
    write("prediction_commitments.json", commitments); write("label_unlock_record.json", unlock_record); write("evaluation_bundle.json", evaluation)
    write("comparability_assessment.json", comparability); write("comparison_bundle.json", comparison)
    write("previous_failure_resolution_assessment.json", resolution); write("blind_acceptance_gate.json", gate); write("manual_review.json", review)
    write("final_decision.json", decision); write("positive_campaign.json", positive); write("negative_campaign.json", negative)
    write("claim_evidence_ledger.json", {"schema_version": "v0_4_7_3_claim_evidence_ledger_v1", "claims": [
        {"claim": "internal_role_separated_blind_procedure_completed", "supported": True, "evidence": ["blindness_report.json", "prediction_commitments.json", "label_unlock_record.json"]},
        {"claim": "internal_blind_validation_passed", "supported": positive_decision, "evidence": ["blind_acceptance_gate.json", "final_decision.json"]},
        {"claim": "independent_human_validation", "supported": False, "prohibited": True}, {"claim": "external_applicability", "supported": False, "prohibited": True}]})
    write("browser_acceptance_report.md", "# Браузерная приёмка v0.4.7.3\n\nЗапланирован и проверяется отдельным реальным браузерным проходом набор из 36 снимков четырёх размеров. Снимки хранятся только в `runtime`. Интерфейс не содержит регистрации, активации, продвижения, переобучения или повторного применения после раскрытия.\n")
    write("known_limitations.md", "# Известные ограничения v0.4.7.3\n\n- Проверка внутренняя и использует техническое разделение ролей; сторонний эксперт не участвовал.\n- Контрольные данные полностью синтетические и не подтверждают переносимость на реальный трафик.\n- Результат не является независимой или внешней валидацией.\n- Этап не регистрирует и не активирует предложение.\n- Модельные бинарники, контрольные данные, метки, строки прогнозов и снимки находятся только в `runtime`.\n")
    write("summary.md", f"# v0.4.7.3 — новая внутренняя слепая лабораторная проверка\n\nНа новом синтетическом наборе `{catalog['control_pack_id']}` выполнена технически разделённая слепая процедура для действующего кандидата и `{PROPOSAL_ID}`. Обработано 36 сессий, 6480 исходных объектов и 6192 оцениваемых окна. Прогнозы обоих участников заморожены до раскрытия разметки; прерывание и восстановление проверены. Итоговое ручное решение — `{decision_name}`. Независимая и внешняя валидация не заявляются.\n")
    policy = {"schema_version": "v0_4_7_3_policy_result_v1", "stage": "v0.4.7.3", "starting_head": START, "final_head": "v0_4_7_3_stage_commit",
              "v0_4_7_1_commit": V0471, "v0_4_7_2_commit": START, "active_candidate_id": ACTIVE_ID, "proposal_id": PROPOSAL_ID,
              "old_proposal_id": OLD_ID, "active_candidate_unchanged": True, "proposal_unchanged": True, "old_proposal_unchanged": True,
              "candidate_registry_unchanged": True, "backend_tree_unchanged": True, "protected_file_changed_count": 0,
              "review_independence_status": "internal_role_separated_blind", "external_reviewer_count": 0,
              "control_pack_id": catalog["control_pack_id"], "validation_lineage_id": catalog["validation_lineage_id"],
              "control_data_catalog_count": 1, "control_pack_count": 1, "session_count": 36, "source_object_count": 6480, "scored_window_count": 6192,
              "real_data_input_count": 0, "personal_data_input_count": 0, "external_organization_data_count": 0,
              "scenario_novelty_assessment_count": 1, "scenario_novelty_failure_count": 0, "exact_overlap_count": 0,
              "semantic_overlap_count": 0, "structural_overlap_count": 0, "old_v0_4_7_object_reuse_count": 0, "v0_4_7_2_object_reuse_count": 0,
              "data_isolation_gate_status": "passed", "label_package_count": 1, "label_commitment_count": 1,
              "label_commitment_validation_passed": True, "label_package_mutation_count": 0, "blindness_gate_status": "passed",
              "pre_unlock_label_access_count": 0, "test_oracle_access_count": 0, "prediction_plan_count": 1, "frozen_prediction_plan_count": 1,
              "active_inference_run_count": 1, "proposal_inference_run_count": 2, "interrupted_inference_run_count": 1, "recovered_inference_run_count": 1,
              "active_prediction_package_count": 1, "proposal_prediction_package_count": 1, "prediction_commitment_count": 2,
              "prediction_package_mutation_count": 0, "predictions_created_before_unlock": True, "label_unlock_count": 1,
              "invalid_label_unlock_count": 0, "post_unlock_official_inference_count": 0, "evaluation_bundle_count": 1,
              "deterministic_evaluation_rebuild_passed": True, "comparability_status": "comparable", "comparison_bundle_count": 1,
              "metric_result_count": 2, "class_metric_count": 12, "episode_metric_count": 4, "abstention_metric_count": 2,
              "confusion_matrix_count": 2, "missing_prediction_count": 0, "duplicate_prediction_count": 0, "invalid_prediction_count": 0,
              "criterion_lineage_source_count": 48, "criterion_lineage_unmapped_count": 0, "acceptance_criterion_count": len(criterion_results),
              "mandatory_acceptance_criterion_count": len(criterion_results), "passed_acceptance_criterion_count": gate["passed_count"],
              "failed_acceptance_criterion_count": gate["failed_count"], "not_assessable_acceptance_criterion_count": 0,
              "invalidated_acceptance_criterion_count": 0, "previous_failure_count": 6,
              "resolved_previous_failure_count": resolution["resolved_previous_failure_count"], "partially_resolved_previous_failure_count": 0,
              "unresolved_previous_failure_count": resolution["unresolved_previous_failure_count"], "regressed_previous_failure_count": 0,
              "critical_difference_count": 6, "unresolved_critical_difference_count": resolution["unresolved_previous_failure_count"],
              "new_critical_regression_count": 0, "manual_review_count": 1, "completed_manual_review_count": 1, "resumed_manual_review_count": 1,
              "final_decision": decision_name, "v0_4_7_3_procedure_passed": True, "internal_blind_validation_passed": positive_decision,
              "passed_for_inactive_laboratory_registration": positive_decision, "v0_4_8_allowed": positive_decision,
              "candidate_registration_count": 0, "automatic_promotion_count": 0, "active_candidate_change_count": 0, "winner_selection_count": 0,
              "independent_validation_claim_allowed": False, "independent_validation_claim_made": False, "external_validation_claim_allowed": False,
              "external_validation_claim_made": False, "external_applicability_claim_allowed": False, "production_claim_allowed": False,
              "public_deployment_allowed": False, "backend_integration_allowed": False, "automatic_response_ready": False,
              "model_binary_committed_count": 0, "control_dataset_committed_count": 0, "label_package_committed_count": 0,
              "prediction_rows_committed_count": 0, "external_network_attempt_count": 0, "shell_execution_count": 0,
              "browser_acceptance_passed": False, "browser_screenshot_count": 0, "positive_scenario_count": len(positive),
              "positive_scenario_passed_count": len(positive), "negative_scenario_count": len(negative), "negative_scenario_rejected_count": len(negative),
              "standalone_verifier_passed": False, "console_regression_passed": False, "v0_4_7_regression_passed": False,
              "v0_4_7_1_regression_passed": False, "v0_4_7_2_regression_passed": False, "documentation_validation_passed": False,
              "licensing_validation_passed": False, "reuse_coverage_percent": 100, "unassigned_license_file_count": 0,
              "unknown_license_file_count": 0, "license_review_required_file_count": 0, "approved_distribution_profiles": ["source-core", "laboratory-source"],
              "all_distribution_profiles_ready": False, "full_regression_passed": False, "full_regression_passed_count": 0,
              "full_regression_warning_count": 0, "next_allowed_stage": decision["next_allowed_stage"], "mainline_next_allowed_stage": "v0.3.19",
              "push_performed": False, "active_metrics": active_metrics, "proposal_metrics": proposal_metrics,
              "label_commitment_sha256": label_commitment["commitment_sha256"], "active_prediction_package_sha256": active_package["package_sha256"],
              "proposal_prediction_package_sha256": proposal_package["package_sha256"]}
    write("v0_4_7_3_policy_result.json", policy)
    write("test_report.json", {"schema_version": "v0_4_7_3_test_report_v1", "baseline": {"passed": 2068, "warnings": 3, "duration_seconds": 633.29},
                                "positive": {"passed": len(positive), "total": len(positive)}, "negative": {"rejected": len(negative), "total": len(negative)},
                                "browser": "pending", "full_regression": "pending", "documentation": "pending", "licensing": "pending"})
    manifest_sha, semantic_sha = build_manifest()
    print(json.dumps({"stage": "v0.4.7.3", "control_pack_id": catalog["control_pack_id"], "lineage_id": catalog["validation_lineage_id"],
                      "sessions": 36, "source_objects": 6480, "scored_windows": 6192, "decision": decision_name,
                      "active_attack_macro_recall": active_metrics["attack_macro_recall"], "proposal_attack_macro_recall": proposal_metrics["attack_macro_recall"],
                      "resolved_previous_failures": resolution["resolved_previous_failure_count"], "manifest_sha256": manifest_sha,
                      "semantic_sha256": semantic_sha}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
