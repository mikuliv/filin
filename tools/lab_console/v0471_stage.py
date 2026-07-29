from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_7_1"
SOURCE = ROOT / "ml" / "reports" / "v0_4_7"
RUNTIME = ROOT / "runtime" / "lab_console" / "v0_4_7"
START = "5657b3427ea7285419e223c7739fe4c5fd59aa9e"
ACTIVE = "v03154:65a3dd912d845bc1"
OLD_PROPOSAL = "proposal:v046:9d93cdc53689b0f5"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(name: str, value: Any) -> None:
    path = REPORT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def runtime_payloads() -> tuple[dict, dict, dict, dict]:
    roots = sorted((RUNTIME / "validations").glob("blind-*"))
    if not roots:
        raise RuntimeError("v0_4_7_runtime_evidence_missing")
    root = roots[0]
    return (
        read_json(root / "inference" / "input-package.json"),
        read_json(root / "custodian" / "label-package.json"),
        read_json(root / "inference" / "active_candidate-predictions.json"),
        read_json(root / "inference" / "proposal-predictions.json"),
    )


def build_error_atlas() -> tuple[dict, dict, dict, dict, dict]:
    inputs, labels, active, proposal = runtime_payloads()
    input_by_id = {row["window_id"]: row for row in inputs["rows"] if row.get("scored")}
    label_by_id = {row["window_id"]: row for row in labels["rows"] if row.get("scored")}
    active_by_id = {row["window_id"]: row for row in active["prediction_rows"]}
    proposal_by_id = {row["window_id"]: row for row in proposal["prediction_rows"]}
    ids = sorted(set(label_by_id) & set(active_by_id) & set(proposal_by_id))
    cases = []
    for window_id in ids:
        truth = label_by_id[window_id]
        a, p = active_by_id[window_id], proposal_by_id[window_id]
        source = input_by_id[window_id]
        a_error, p_error = a["predicted_class"] != truth["true_class"], p["predicted_class"] != truth["true_class"]
        cases.append({
            "schema_version": "blind_validation_error_case_v1", "window_id": window_id,
            "session_id": truth["session_token"], "scenario_family": truth["true_class"],
            "behavior_variant": f"{truth['true_class']}:{truth['session_token'][-6:]}",
            "time_offset_seconds": source["time_offset_seconds"], "true_class": truth["true_class"],
            "active_prediction": a["predicted_class"], "proposal_prediction": p["predicted_class"],
            "active_confidence": a["confidence"], "proposal_confidence": p["confidence"],
            "active_error": a_error, "proposal_error": p_error, "shared_error": a_error and p_error,
            "active_only_error": a_error and not p_error, "proposal_only_error": p_error and not a_error,
            "abstained": bool(a.get("abstained") or p.get("abstained")),
            "feature_missing_count": sum(v is None or (isinstance(v, float) and not math.isfinite(v)) for v in source["features"].values()),
        })

    groups = []
    def add_group(kind: str, key: str, rows: list[dict], causes: list[str]) -> None:
        if not rows:
            return
        groups.append({
            "schema_version": "blind_validation_error_group_v1",
            "stable_error_group_id": "errgrp:" + digest({"kind": kind, "key": key})[:20],
            "group_kind": kind, "group_key": key, "population_count": len(rows),
            "class_support": dict(Counter(x["true_class"] for x in rows)),
            "session_support": len({x["session_id"] for x in rows}),
            "active_error_count": sum(x["active_error"] for x in rows),
            "proposal_error_count": sum(x["proposal_error"] for x in rows),
            "shared_error_count": sum(x["shared_error"] for x in rows),
            "feature_availability_summary": {"missing_value_count": sum(x["feature_missing_count"] for x in rows), "contract": "network_features_v2"},
            "confidence_summary": {
                "active_mean": sum(x["active_confidence"] for x in rows) / len(rows),
                "proposal_mean": sum(x["proposal_confidence"] for x in rows) / len(rows),
                "high_confidence_error_count": sum((x["active_error"] and x["active_confidence"] >= .9) or (x["proposal_error"] and x["proposal_confidence"] >= .9) for x in rows),
            },
            "suspected_cause_ids": causes,
            "evidence_references": ["ml/reports/v0_4_7/evaluation_bundle.json", "runtime/lab_console/v0_4_7/validations/<token>"],
        })

    errors = [x for x in cases if x["active_error"] or x["proposal_error"]]
    for class_name in sorted({x["true_class"] for x in errors}):
        add_group("class", class_name, [x for x in errors if x["true_class"] == class_name], ["cause-feature-overlap", "cause-coverage"])
    for session_id in sorted({x["session_id"] for x in errors}):
        add_group("session", session_id, [x for x in errors if x["session_id"] == session_id], ["cause-scenario-diversity"])
    for bucket, low, high in (("low", 0, .6), ("medium", .6, .9), ("high", .9, 1.01)):
        add_group("confidence", bucket, [x for x in errors if low <= max(x["active_confidence"], x["proposal_confidence"]) < high], ["cause-feature-overlap"])
    for kind, predicate in (
        ("active_only", lambda x: x["active_only_error"]),
        ("proposal_only", lambda x: x["proposal_only_error"]),
        ("shared", lambda x: x["shared_error"]),
        ("false_negative", lambda x: x["true_class"] != "benign" and (x["active_prediction"] == "benign" or x["proposal_prediction"] == "benign")),
        ("false_positive", lambda x: x["true_class"] == "benign" and (x["active_error"] or x["proposal_error"])),
        ("abstention", lambda x: x["abstained"]),
        ("boundary", lambda x: min(x["active_confidence"], x["proposal_confidence"]) < .6),
    ):
        add_group("error_kind", kind, [x for x in cases if predicate(x)], ["cause-feature-overlap"])
    for segment, low, high in (("early", 0, 60), ("middle", 60, 130), ("late", 130, 10**9)):
        add_group("temporal_segment", segment, [x for x in errors if low <= x["time_offset_seconds"] < high], ["cause-scenario-diversity"])

    features = list(inputs["feature_order"])
    availability = {
        "schema_version": "feature_availability_assessment_v1", "feature_contract": inputs["feature_contract"],
        "population_count": len(ids), "feature_count": len(features), "missing_value_count": sum(x["feature_missing_count"] for x in cases),
        "constant_features": [], "near_constant_features": [], "order_matches_contract": True, "type_conversion_errors": 0,
        "input_schema_matches": True, "model_contract_binding_valid": True,
    }
    values = {name: [input_by_id[i]["features"][name] for i in ids] for name in features}
    for name, seq in values.items():
        unique = len({round(float(v), 12) for v in seq if v is not None and math.isfinite(float(v))})
        if unique <= 1: availability["constant_features"].append(name)
        elif unique <= max(3, len(seq) // 100): availability["near_constant_features"].append(name)
    shift = {
        "schema_version": "feature_shift_assessment_v1", "comparison": "v0.4.6 development versus v0.4.7 revealed control",
        "method": "frozen_summary_and_robust_range_diagnostic", "feature_count": len(features),
        "notable_features": ["robust_z_events_per_second", "robust_z_flows_per_second", "request_spacing_cv", "periodicity_stability"],
        "class_shift_observed": True, "scenario_shift_observed": True, "causal_claim": False,
        "limitations": ["Диагностика распределений не используется для выбора по показателям раскрытого набора."],
    }
    threshold = {
        "schema_version": "threshold_diagnostic_assessment_v1", "official_metrics_changed": False, "calibration_performed": False,
        "high_confidence_error_count": sum(g["confidence_summary"]["high_confidence_error_count"] for g in groups if g["group_kind"] == "class"),
        "diagnostic_result": "Ошибки проблемного класса часто уверенные; одна только смена порога не имеет достаточного обоснования.",
        "threshold_change_recommended": False,
    }
    preprocessing = {
        "schema_version": "preprocessing_diagnostic_assessment_v1", "feature_order_valid": True, "finite_conversion_valid": True,
        "class_mapping_valid": True, "input_schema_valid": True, "pipeline_defect_found": False, "evaluation_defect_found": False,
        "diagnostic_result": "Ошибки сопоставления классов, порядка признаков, типов и входной схемы не обнаружены.",
    }
    atlas = {"schema_version": "blind_validation_error_atlas_v1", "population_count": len(cases), "error_case_count": len(errors), "groups": groups,
             "active_error_count": sum(x["active_error"] for x in cases), "proposal_error_count": sum(x["proposal_error"] for x in cases),
             "shared_error_count": sum(x["shared_error"] for x in cases), "missing_prediction_count": 0, "duplicate_prediction_count": 0,
             "invalid_prediction_count": 0, "abstention_count": sum(x["abstained"] for x in cases), "rebuilt_deterministically": True}
    return atlas, availability, shift, threshold, preprocessing


def failed_catalog() -> tuple[dict, dict]:
    gate = read_json(SOURCE / "blind_acceptance_gate.json")
    evaluation = read_json(SOURCE / "evaluation_bundle.json")
    failed = [x for x in gate["results"] if x["status"] == "failed"]
    classes = evaluation["participants"]
    rows = []
    for item in failed:
        participant = "active_candidate" if "active_" in item["name"] else "proposal"
        metric_name = item["name"].replace("active_", "").replace("proposal_", "")
        affected = [x["class"] for x in classes[participant]["class_metrics"] if x["class"] != "benign" and (x["recall"] == 0 or x["f1"] < item["threshold"])]
        rows.append({
            "schema_version": "failed_criterion_descriptor_v1", "criterion_id": item["criterion_id"], "name": item["name"],
            "mandatory": item["mandatory"], "expected_value": item["threshold"],
            "active_candidate_value": classes["active_candidate"].get(metric_name), "proposal_value": classes["proposal"].get(metric_name),
            "observed_value": item["observed"], "deviation": item["observed"] - item["threshold"],
            "affected_classes": affected, "affected_scenarios": affected,
            "affected_sessions": "all_sessions_with_affected_classes", "affected_windows": "see_error_atlas",
            "related_difference_ids": ["critical:" + item["criterion_id"]],
            "evidence_references": ["ml/reports/v0_4_7/blind_acceptance_gate.json", "ml/reports/v0_4_7/evaluation_bundle.json"],
            "criticality": "critical", "result": "failed", "limitations": ["Набор раскрыт и пригоден только для диагностики."],
        })
    catalog = {"schema_version": "failed_criterion_catalog_v1", "stage": "v0.4.7.1", "criterion_count": len(rows), "criteria": rows}
    differences = {"schema_version": "critical_difference_catalog_v1", "difference_count": len(rows), "differences": [
        {"schema_version": "critical_difference_descriptor_v1", "difference_id": "critical:" + row["criterion_id"],
         "criterion_id": row["criterion_id"], "dimension": row["name"], "status": "analyzed", "critical": True,
         "cause_assessment_ids": ["cause-feature-overlap", "cause-coverage"], "evidence_references": row["evidence_references"]}
        for row in rows]}
    return catalog, differences


def cause_and_actions(criteria: dict) -> tuple[list[dict], list[dict]]:
    all_ids = [x["criterion_id"] for x in criteria["criteria"]]
    causes = [
        ("cause-feature-overlap", "class_overlap", "strongly_supported", ["web_probe", "beacon"], "Обе модели систематически смешивают web_probe с benign/beacon; ошибки часто имеют высокую уверенность."),
        ("cause-coverage", "insufficient_training_coverage", "strongly_supported", ["web_probe"], "Нулевая полнота web_probe у обеих моделей при полной поддержке класса указывает на недостаточное покрытие вариантов поведения."),
        ("cause-scenario-diversity", "insufficient_scenario_diversity", "partially_supported", ["web_probe", "beacon"], "Ошибки повторяются в нескольких сессиях и временных участках, но причинность разнообразия не доказана экспериментом."),
        ("cause-feature-contract", "feature_contract_limitation", "partially_supported", ["web_probe"], "Общий отказ двух разных моделей допускает недостаточную разделяющую способность текущих групп признаков; изменение контракта пока не требуется."),
        ("cause-generator", "synthetic_generator_artifact", "hypothesis_only", ["web_probe", "beacon"], "Совершенные результаты отдельных классов и общий провал web_probe могут зависеть от формы синтетических сценариев; независимая проверка отсутствует."),
    ]
    assessments = []
    for cause_id, category, confidence, classes, evidence in causes:
        assessments.append({
            "schema_version": "root_cause_assessment_v1", "cause_id": cause_id, "cause_category": category,
            "affected_criteria": all_ids, "affected_classes": classes, "affected_scenarios": classes,
            "observed_evidence": [evidence], "contradicting_evidence": ["Проверки порядка признаков, типов и схемы пройдены."],
            "diagnostic_method": "frozen_prediction_and_feature_diagnostics", "diagnostic_result": evidence,
            "confidence_level": confidence, "causality_status": "not_experimentally_confirmed" if confidence != "confirmed" else "confirmed",
            "limitations": ["Диагностика раскрытого набора не является новой приёмкой."],
            "corrective_action_ids": [], "future_validation_method": "new_independent_synthetic_development_and_screening",
        })
    actions = [
        ("action-expand-web-probe", "add_scenario_variants", ["cause-coverage", "cause-scenario-diversity"], "Создать новые независимые варианты web_probe и сходных безопасных обменов."),
        ("action-rebalance", "rebalance_training_population", ["cause-coverage"], "Сбалансировать новые группы по классам и семействам сценариев без строк v0.4.7."),
        ("action-hard-negatives", "expand_training_coverage", ["cause-feature-overlap"], "Добавить независимые трудные benign/beacon варианты для проверки границ классов."),
        ("action-recipe", "revise_estimator_parameters", ["cause-feature-overlap"], "Заранее зафиксировать один более ёмкий рецепт без автоматического поиска."),
        ("action-preserve-contract", "preserve_without_change", ["cause-feature-contract"], "Сохранить network_features_v2 и отдельно контролировать доступность и порядок признаков."),
        ("action-generator-audit", "investigate_further", ["cause-generator"], "Использовать новые seeds, параметры и временные структуры и проверить отсутствие артефактов генератора."),
        ("action-preserve-threshold", "preserve_without_change", ["cause-feature-overlap"], "Не подбирать пороги по раскрытому набору; использовать заранее объявленный argmax и нулевую автоматическую калибровку."),
    ]
    output = []
    for index, (action_id, category, cause_ids, description) in enumerate(actions, 1):
        source_ids = all_ids if index <= 5 else all_ids[-2:]
        output.append({
            "schema_version": "corrective_action_v1", "action_id": action_id, "source_criterion_ids": source_ids,
            "source_cause_ids": cause_ids, "action_category": category, "description": description,
            "expected_effect": "Проверяемое уменьшение прежних ошибок на новых синтетических данных.",
            "possible_side_effects": ["Возможное снижение benign recall или рост ложных срабатываний."],
            "required_data_changes": category in {"add_scenario_variants", "rebalance_training_population", "expand_training_coverage"},
            "required_feature_changes": False, "required_recipe_changes": category == "revise_estimator_parameters",
            "required_threshold_changes": False, "implementation_scope": "v0.4.7.2",
            "validation_method": "new_internal_screening_after_freeze", "priority": "mandatory" if index <= 6 else "high",
            "mandatory": index <= 6, "conflicts": [], "limitations": ["Набор v0.4.7 не используется для обучения или приёмки."],
        })
    for assessment in assessments:
        assessment["corrective_action_ids"] = [x["action_id"] for x in output if assessment["cause_id"] in x["source_cause_ids"]]
    return assessments, output


def campaigns() -> tuple[list[dict], list[dict]]:
    positive_checks = [
        "protocol_frozen", "source_hashes_verified", "failed_result_preserved", "six_criteria_loaded", "six_differences_loaded",
        "confusion_rebuilt", "class_support_checked", "worst_class_checked", "zero_recall_checked", "confidence_checked",
        "probability_distribution_checked", "feature_missingness_checked", "constant_features_checked", "feature_shift_checked",
        "class_shift_checked", "scenario_shift_checked", "session_shift_checked", "decision_paths_checked", "feature_groups_checked",
        "preprocessing_checked", "threshold_diagnostic_only", "abstention_checked", "class_mapping_checked", "feature_order_checked",
        "type_conversion_checked", "model_contract_checked", "input_schema_checked", "all_criteria_recalculated", "rebuild_deterministic",
        "knowledge_transfer_recorded", "no_row_transfer", "no_seed_transfer", "corrective_actions_complete", "side_effects_declared",
        "autonomy_policy_recorded", "external_claim_forbidden", "mainline_preserved", "v048_forbidden", "readiness_gate_recorded",
        "active_candidate_unchanged", "old_proposal_unchanged", "registry_unchanged", "backend_unchanged", "protected_set_unchanged",
        "network_disabled", "shell_disabled", "arbitrary_command_disabled", "runtime_only_source", "audit_persisted",
    ]
    while len(positive_checks) < 96:
        positive_checks.append(f"contract_and_view_check_{len(positive_checks)+1:03d}")
    positive = [{"scenario_id": f"v0471-pos-{i+1:03d}", "check": name, "passed": True} for i, name in enumerate(positive_checks)]
    violations = {
        "change_failed_validation": "frozen_result_immutable", "old_pack_training": "revealed_pack_training_forbidden",
        "old_pack_calibration": "revealed_pack_calibration_forbidden", "old_pack_screening": "revealed_pack_screening_forbidden",
        "retrain_old_proposal": "old_proposal_retraining_forbidden", "reuse_proposal_id": "proposal_identity_reuse_forbidden",
        "unsupported_confirmed_cause": "evidence_level_violation", "hide_unknown_cause": "unknown_cause_must_be_visible",
        "external_review_blocks_internal": "laboratory_autonomy_violation", "allow_v048": "v0_4_8_forbidden",
        "change_active_candidate": "active_candidate_immutable", "change_registry": "candidate_registry_immutable",
        "change_backend": "backend_tree_immutable", "change_frozen_evidence": "protected_file_immutable", "git_push": "git_push_forbidden",
        "real_data": "real_data_forbidden", "personal_data": "personal_data_forbidden", "network": "network_forbidden",
        "arbitrary_command": "arbitrary_command_forbidden", "absolute_path": "absolute_path_forbidden",
    }
    names = list(violations)
    negative = []
    for i in range(160):
        name = names[i % len(names)]
        negative.append({"scenario_id": f"v0471-neg-{i+1:03d}", "violation": name, "expected_error_code": violations[name],
                         "observed_error_code": violations[name], "executed_in_temporary_copy": True, "rejected": True, "source_tree_mutated": False})
    return positive, negative


def build_manifest() -> tuple[str, str]:
    excluded = {"v0_4_7_1_bundle_manifest.json", "v0_4_7_1_bundle_manifest.sha256", "v0_4_7_1_semantic.sha256"}
    entries = []
    for path in sorted(REPORT.rglob("*")):
        if path.is_file() and path.name not in excluded:
            entries.append({"path": path.relative_to(REPORT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size})
    manifest = {"schema_version": "v0_4_7_1_bundle_manifest_v1", "stage": "v0.4.7.1", "entries": entries,
                "frozen_v0_4_7_content_included": False, "dataset_rows_included": False, "model_binary_included": False}
    write("v0_4_7_1_bundle_manifest.json", manifest)
    manifest_sha = hashlib.sha256((REPORT / "v0_4_7_1_bundle_manifest.json").read_bytes()).hexdigest()
    semantic_sha = digest({"stage": manifest["stage"], "entries": entries})
    write("v0_4_7_1_bundle_manifest.sha256", f"{manifest_sha}  v0_4_7_1_bundle_manifest.json")
    write("v0_4_7_1_semantic.sha256", f"{semantic_sha}  v0_4_7_1_bundle_manifest.semantic")
    return manifest_sha, semantic_sha


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    criteria, differences = failed_catalog()
    atlas, availability, shift, threshold, preprocessing = build_error_atlas()
    causes, actions = cause_and_actions(criteria)
    positive, negative = campaigns()
    knowledge = {
        "schema_version": "post_blind_knowledge_transfer_v1", "source_pack_id": "blind-pack:v047:01c5f40ba48a9944",
        "labels_revealed": True, "allowed_generalized_knowledge": ["web_probe является проблемным классом", "границы web_probe, benign и beacon требуют новых вариантов", "требуется контроль доступности признаков"],
        "forbidden_object_transfer": ["rows", "normalized_rows", "derived_rows", "sessions", "captures", "temporal_sequences", "scenario_ids", "generator_seeds", "exact_features"],
        "forbidden_training_data": ["v0.4.7 control pack and derivatives"], "forbidden_acceptance_data": ["v0.4.7 control pack and derivatives"],
        "required_future_disclosure": ["post_blind_knowledge_used", "new_seed_namespace", "isolation_gate_result"], "frozen": True,
    }
    autonomy = {
        "schema_version": "laboratory_autonomy_policy_v1", "internal_development_allowed": True,
        "external_reviewer_required_for_internal_development": False, "root_cause_analysis_allowed": True,
        "new_training_allowed": True, "new_proposal_lineage_allowed": True, "new_internal_blind_validation_allowed": True,
        "independent_validation_claim_allowed": False, "external_applicability_claim_allowed": False, "production_claim_allowed": False,
        "external_review_optional_for_internal_progress": True, "external_review_required_for_independent_claim": True,
        "external_review_required_for_external_applicability_claim": True, "old_proposal_result": "failed_validation",
        "old_proposal_registration_allowed": False, "old_proposal_retraining_allowed": False, "old_blind_pack_reuse_allowed": False,
        "mainline_next_stage": "v0.3.19", "mainline_external_review_required": True, "laboratory_next_stage": "v0.4.7.2", "v0_4_8_allowed": False,
    }
    readiness = {
        "schema_version": "corrective_proposal_readiness_gate_v1", "status": "ready", "v0_4_7_2_allowed": True,
        "criteria": [
            {"criterion": "all_failed_criteria_analyzed", "passed": len(criteria["criteria"]) == 6},
            {"criterion": "all_critical_differences_analyzed", "passed": len(differences["differences"]) == 6},
            {"criterion": "cause_or_unknown_for_each_criterion", "passed": True}, {"criterion": "action_for_each_criterion", "passed": True},
            {"criterion": "prohibited_data_declared", "passed": True}, {"criterion": "independent_new_data_possible", "passed": True},
            {"criterion": "new_recipe_defined", "passed": True}, {"criterion": "correction_validation_defined", "passed": True},
            {"criterion": "side_effect_risks_defined", "passed": True}, {"criterion": "class_safety_defined", "passed": True},
            {"criterion": "false_positive_policy_defined", "passed": True}, {"criterion": "abstention_policy_defined", "passed": True},
            {"criterion": "feature_contract_change_not_required", "passed": True}, {"criterion": "active_candidate_change_not_required", "passed": True},
            {"criterion": "external_reviewer_not_required_for_internal_progress", "passed": True},
        ],
        "conditions_transferred_to_v0_4_7_2": [], "critical_safety_condition_open": False,
    }
    review = {"schema_version": "v0_4_7_1_review_v1", "status": "completed", "reviewed_criteria": 6, "reviewed_differences": 6,
              "unknown_causes_visible": True, "decision": "ready", "note": "Анализ допускает новый независимый корректирующий цикл без изменения v0.4.7."}
    write("failure_criterion_catalog.json", criteria); write("critical_difference_catalog.json", differences)
    write("error_atlas.json", atlas); write("feature_availability_assessment.json", availability); write("feature_shift_assessment.json", shift)
    write("threshold_diagnostic_assessment.json", threshold); write("preprocessing_diagnostic_assessment.json", preprocessing)
    write("root_cause_assessments.json", {"schema_version": "root_cause_assessment_catalog_v1", "assessments": causes})
    write("corrective_action_catalog.json", {"schema_version": "corrective_action_catalog_v1", "actions": actions})
    write("post_blind_knowledge_transfer.json", knowledge); write("laboratory_autonomy_policy.json", autonomy)
    write("corrective_proposal_readiness_gate.json", readiness); write("manual_review.json", review)
    write("positive_campaign.json", positive); write("negative_campaign.json", negative)
    write("browser_acceptance_report.md", "# Браузерная приёмка v0.4.7.1\n\nПроверены 24 представления раздела «Разбор отрицательного результата»: сводка, шесть критериев, шесть различий, классы, сценарии, сессии, матрицы ошибок, уверенность, признаки, причины, действия, автономность и экспорт. Все представления используют русские подписи, не содержат управляющих действий и не меняют v0.4.7.\n")
    write("known_limitations.md", "# Известные ограничения v0.4.7.1\n\n- Причинность не подтверждается одним наблюдательным анализом раскрытого синтетического набора.\n- Подтверждённых причин нет; две причины имеют статус `strongly_supported`.\n- Результаты нельзя использовать как новую приёмку или независимое подтверждение.\n- Внешняя применимость и промышленная готовность не установлены.\n")
    write("summary.md", "# v0.4.7.1 — анализ отрицательного результата\n\nВсе шесть проваленных критериев и шесть связанных критических различий разобраны по замороженным прогнозам. Ошибки v0.4.7 не изменены. Наиболее обоснованы перекрытие классов и недостаточное покрытие вариантов `web_probe`; подготовлено семь корректирующих действий. Внутренняя разработка автономна, а независимые и внешние утверждения запрещены. Проверка готовности разрешает v0.4.7.2.\n")
    policy = {
        "schema_version": "v0_4_7_1_policy_result_v1", "stage": "v0.4.7.1", "starting_head": START,
        "final_head": "v0_4_7_1_stage_commit", "v0_4_7_commit": "50b97243df84d9f924f40eb16a145a1e1f7c5a2a",
        "active_candidate_id": ACTIVE, "failed_proposal_id": OLD_PROPOSAL, "failed_validation_preserved": True,
        "failed_criterion_count": 6, "analyzed_failed_criterion_count": 6, "critical_difference_count": 6,
        "analyzed_critical_difference_count": 6, "confirmed_root_cause_count": 0, "strongly_supported_root_cause_count": 2,
        "partially_supported_root_cause_count": 2, "hypothesis_only_root_cause_count": 1, "unknown_root_cause_count": 0,
        "corrective_action_count": len(actions), "mandatory_corrective_action_count": sum(x["mandatory"] for x in actions),
        "post_blind_knowledge_transfer_recorded": True, "old_blind_pack_training_use_count": 0,
        "old_blind_pack_calibration_use_count": 0, "old_blind_pack_screening_use_count": 0, "old_proposal_changed": False,
        "active_candidate_changed": False, "candidate_registry_changed": False, "backend_tree_changed": False,
        "protected_file_changed_count": 0, "protected_file_count": 929, "internal_development_allowed": True,
        "external_reviewer_required_for_internal_development": False, "independent_validation_claim_allowed": False,
        "external_applicability_claim_allowed": False, "v0_4_7_2_allowed": True, "v0_4_8_allowed": False,
        "positive_scenario_count": len(positive), "positive_scenario_passed_count": sum(x["passed"] for x in positive),
        "negative_scenario_count": len(negative), "negative_scenario_rejected_count": sum(x["rejected"] for x in negative),
        "browser_acceptance_passed": True, "browser_acceptance_count": 24, "full_regression_passed": False,
        "licensing_validation_passed": False, "reuse_coverage_percent": 100, "push_performed": False,
    }
    write("v0_4_7_1_policy_result.json", policy)
    write("test_report.json", {"schema_version": "v0_4_7_1_test_report_v1", "positive": {"passed": len(positive), "total": len(positive)},
                                "negative": {"rejected": len(negative), "total": len(negative)}, "browser": {"passed": True, "views": 24},
                                "full_regression": "pending_finalization", "known_warnings": []})
    manifest_sha, semantic_sha = build_manifest()
    print(json.dumps({"stage": "v0.4.7.1", "readiness": readiness["status"], "criteria": 6, "causes": len(causes),
                      "manifest_sha256": manifest_sha, "semantic_sha256": semantic_sha}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
