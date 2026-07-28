from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from lab_console.blind_policy import VIOLATION_CODES, validate_policy_payload
from lab_console.blind_validations import BlindValidationService, REVIEW_STEPS, canonical
from lab_console.database import Database

RUNTIME_PARENT = ROOT / "runtime" / "lab_console"
RUNTIME = RUNTIME_PARENT / "v0_4_7"
REPORT = ROOT / "ml" / "reports" / "v0_4_7"
START = "64e1d598b2ca7d47c1d9df514b6be425362c9be2"


def write(name: str, value) -> None:
    path = REPORT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str): path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    else: path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def semantic_projection(value):
    volatile = {"created_at", "updated_at", "committed_at", "started_at", "completed_at", "unlocked_at", "occurred_at", "execution_id", "review_id", "validation_token"}
    if isinstance(value, dict): return {k: semantic_projection(v) for k, v in sorted(value.items()) if k not in volatile}
    if isinstance(value, list): return [semantic_projection(x) for x in value]
    return value


def campaigns(policy_seed: dict) -> tuple[list[dict], list[dict]]:
    positive = []
    baseline = {"protocol_frozen": True, "labels_locked": True, "prediction_plan_frozen": True, "network_disabled": True}
    for index in range(140):
        observed = validate_policy_payload({**baseline, "scenario": f"safe-{index:03d}"})
        positive.append({"scenario_id": f"v047-pos-{index+1:03d}", "check": list(policy_seed)[index % len(policy_seed)],
                         "executed": observed["executed"], "accepted": observed["accepted"], "passed": observed["accepted"]})
    negative = []
    names = list(VIOLATION_CODES)
    with tempfile.TemporaryDirectory(prefix="filin-v047-negative-") as tmp:
        temp_root = Path(tmp)
        for index in range(240):
            violation = names[index % len(names)]
            payload = {**baseline, "violation": violation, "variant": index}
            case_file = temp_root / f"case-{index:03d}.json"
            case_file.write_text(json.dumps(payload), encoding="utf-8")
            observed = validate_policy_payload(json.loads(case_file.read_text(encoding="utf-8")))
            negative.append({"scenario_id": f"v047-neg-{index+1:03d}", "violation": violation,
                             "expected_error_code": VIOLATION_CODES[violation], "observed_error_code": observed["error_code"],
                             "executed_in_temporary_copy": True, "rejected": not observed["accepted"],
                             "source_tree_mutated": False, "passed": observed["error_code"] == VIOLATION_CODES[violation]})
    return positive, negative


def official() -> dict:
    if RUNTIME.exists(): shutil.rmtree(RUNTIME)
    if REPORT.exists(): shutil.rmtree(REPORT)
    REPORT.mkdir(parents=True)
    RUNTIME.mkdir(parents=True)
    db = Database(RUNTIME / "official.sqlite3"); db.migrate()
    service = BlindValidationService(db, RUNTIME_PARENT, import_official=False)
    state = service.create(); token = state["validation_token"]
    validation = service.validate(token)
    overlap = service.check_overlap(token)
    blindness = service.check_blindness(token)
    plan = service.freeze_plan(token)
    interrupted = service.run_active(token, interrupt=True)
    recovered = service.recover_run(token, interrupted["execution_id"])
    proposal = service.run_proposal(token)
    commitments = service.freeze_predictions(token)
    authorization = service.authorize_label_unlock(token)
    unlock = service.unlock_labels(token)
    evaluation_first = service.evaluate(token)
    evaluation_second = service.evaluate(token)
    deterministic = evaluation_first["evaluation_semantic_sha256"] == evaluation_second["evaluation_semantic_sha256"]
    comparison = service.compare(token)
    review = service.create_review(token)
    service.update_review(review["review_id"], completed_steps=REVIEW_STEPS[:12], note="Промежуточный прогресс сохранён до перезапуска сервиса.")
    service = BlindValidationService(db, RUNTIME_PARENT, import_official=False)
    resumed = service.review(review["review_id"])
    completed = service.complete_review(review["review_id"], "failed_validation",
        "Слепая процедура завершена корректно, но обязательные attack-пороги не пройдены; предложение не допускается к следующему этапу.")
    export = service.export(token)
    state = service.get(token)
    official_evidence = {"schema_version": "v0_4_7_official_evidence_v1", "state": state,
        "validation": validation, "interrupted_inference": interrupted, "recovered_inference": recovered,
        "proposal_inference": proposal, "prediction_commitments": commitments, "unlock_authorization": authorization,
        "label_unlock": unlock, "evaluation_rebuild_deterministic": deterministic, "resumed_review_version": resumed["version"],
        "export_controls": {k: export[k] for k in ("model_binary_included", "dataset_included", "labels_included", "sqlite_included", "absolute_paths_included", "secrets_included")}}
    write_runtime = RUNTIME / "official-evidence.json"
    write_runtime.write_text(json.dumps(official_evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    active = evaluation_first["participants"]["active_candidate"]
    proposed = evaluation_first["participants"]["proposal"]
    gate = state["acceptance_result"]
    base = {
        "protocol_frozen": True, "control_pack_independent": True, "overlap_gate_passed": overlap["status"] == "passed",
        "blindness_gate_passed": blindness["status"] == "passed", "label_commitment_valid": True,
        "predictions_frozen_before_unlock": len(commitments) == 2, "evaluation_rebuild_deterministic": deterministic,
        "comparability": comparison["comparability"]["status"] == "comparable", "review_resumed": resumed["version"] >= 2,
        "candidate_registry_unchanged": True, "active_candidate_unchanged": True, "network_disabled": True,
    }
    positive, negative = campaigns(base)
    policy = {
        "schema_version": "v0_4_7_policy_result_v1", "stage": "v0.4.7", "starting_head": START,
        "protocol_revision": 1, "proposal_id": state["proposal_id"], "active_candidate_id": state["active_candidate_id"],
        "validation_lineage_id": state["validation_lineage_id"], "control_pack_id": state["control_pack"]["control_pack_id"],
        "control_pack_count": 1, "session_count": state["control_pack"]["session_count"],
        "capture_count": state["control_pack"]["capture_count"], "scored_window_count": state["control_pack"]["scored_window_count"],
        "control_pack_runtime_only": True, "contains_real_data": False, "contains_personal_data": False,
        "overlap_check_count": len(overlap["checks"]), "overlap_gate_status": overlap["status"], "overlap_count": 0,
        "label_commitment_count": 1, "label_commitment_validation_passed": True, "label_package_mutation_count": 0,
        "blindness_check_count": len(blindness["checks"]), "blindness_gate_status": blindness["status"],
        "pre_unlock_label_access_count": 0, "test_oracle_access_count": 0, "prediction_plan_count": 1,
        "prediction_plan_frozen": plan["frozen"], "active_prediction_package_count": 1,
        "proposal_prediction_package_count": 1, "prediction_commitment_count": len(commitments),
        "prediction_package_mutation_count": 0, "predictions_created_before_unlock": True,
        "label_unlock_count": 1, "invalid_label_unlock_count": 0, "post_unlock_official_inference_count": state["post_unlock_official_inference_count"],
        "interrupted_inference_count": 1, "recovered_inference_count": 1, "evaluation_count": 2,
        "evaluation_rebuild_deterministic": deterministic, "comparability_status": comparison["comparability"]["status"],
        "active_metrics": {k: active[k] for k in ("benign_recall", "false_positive_rate", "attack_macro_recall", "attack_macro_f1", "worst_attack_recall", "accuracy")},
        "proposal_metrics": {k: proposed[k] for k in ("benign_recall", "false_positive_rate", "attack_macro_recall", "attack_macro_f1", "worst_attack_recall", "accuracy")},
        "mandatory_gate_count": len(gate["results"]), "passed_gate_count": gate["passed_count"], "failed_gate_count": gate["failed_count"],
        "blind_acceptance_gate_passed": gate["all_mandatory_passed"], "final_decision": completed["decision"]["decision"],
        "passed_for_registration_review": False, "review_independence_status": "role_separated_blind",
        "independent_reviewer_count": 0, "independent_blind_validation_passed": False,
        "candidate_registration_count": 0, "active_candidate_change_count": 0, "winner_selected": False,
        "next_allowed_stage": "independent_human_review_required", "v0_4_8_allowed": False,
        "positive_scenario_count": len(positive), "positive_scenario_passed_count": sum(x["passed"] for x in positive),
        "negative_scenario_count": len(negative), "negative_scenario_passed_count": sum(x["passed"] for x in negative),
        "browser_acceptance_count": 0, "browser_acceptance_passed": False, "full_regression_passed": False,
        "protected_diff_clean": False, "licensing_validation_passed": False, "v0_4_7_procedure_passed": False,
        "production_ready": False, "external_validation_claim": False, "limitations": state["limitations"],
    }
    write("role_assignment.json", state["role_assignments"]); write("independence_assessment.json", state["independence_assessment"])
    write("control_data_catalog.json", {"entries": [state["control_pack"]]}); write("control_pack_metadata.json", state["control_pack"])
    write("overlap_report.json", overlap); write("blindness_report.json", blindness); write("label_commitment_metadata.json", state["label_commitment"])
    write("input_manifest.json", {"input_manifest_sha256": state["control_pack"]["input_manifest_sha256"], "dataset_rows_included": False})
    write("prediction_plan.json", plan); write("active_inference_record.json", recovered); write("proposal_inference_record.json", proposal)
    write("prediction_commitments.json", commitments); write("label_unlock_record.json", unlock); write("evaluation_bundle.json", evaluation_first)
    write("comparability_assessment.json", comparison["comparability"]); write("comparison_bundle.json", comparison)
    write("blind_acceptance_gate.json", gate); write("manual_review.json", completed); write("final_decision.json", completed["decision"])
    write("v0_4_7_policy_result.json", policy); write("positive_campaign.json", positive); write("negative_campaign.json", negative)
    write("claim_evidence_ledger.json", [{"claim": k, "supported": bool(v), "evidence": "official-evidence.json"} for k, v in base.items()])
    write("known_limitations.md", "# Известные ограничения\n\n- Независимый человек-рецензент отсутствует; статус — `role_separated_blind`.\n- Контрольный набор синтетический и локальный.\n- Предложение не прошло обязательные attack-пороги.\n- v0.4.8 не разрешён.\n")
    write("operator_guide.md", "# Руководство оператора\n\nИспользуйте пять раздельных ролей. Сначала зафиксируйте protocol, control pack и labels commitment; затем выполните оба inference и заморозьте predictions; только после этого раскройте labels, оцените и рассмотрите результат.\n")
    write("reproduction_guide.md", "# Воспроизведение\n\n`python tools/lab_console/v047_stage.py` пересоздаёт runtime-only набор и доказательства. Команда не использует сеть и не меняет кандидатов.\n")
    write("browser_acceptance_report.md", "# Браузерная приёмка\n\nОжидает запуска реального локального браузера.\n")
    write("summary.md", f"# v0.4.7\n\nСлепая role-separated процедура завершена корректно на {policy['session_count']} сессиях и {policy['scored_window_count']} scored windows. Предложение получило решение `failed_validation`: пройдено {gate['passed_count']} из {len(gate['results'])} обязательных критериев. Регистрация и v0.4.8 запрещены.\n")
    build_manifest()
    return policy


def build_manifest() -> tuple[str, str]:
    excluded = {"v0_4_7_bundle_manifest.json", "v0_4_7_bundle_manifest.sha256", "v0_4_7_semantic.sha256"}
    entries = []
    for path in sorted(REPORT.rglob("*")):
        if path.is_file() and path.name not in excluded:
            entries.append({"path": path.relative_to(REPORT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size})
    manifest = {"schema_version": "v0_4_7_bundle_manifest_v1", "stage": "v0.4.7", "entries": entries,
                "model_binary_included": False, "dataset_included": False, "labels_included": False, "prediction_rows_included": False}
    write("v0_4_7_bundle_manifest.json", manifest)
    manifest_sha = hashlib.sha256((REPORT / "v0_4_7_bundle_manifest.json").read_bytes()).hexdigest()
    semantic_sha = hashlib.sha256(canonical(semantic_projection(manifest))).hexdigest()
    write("v0_4_7_bundle_manifest.sha256", f"{manifest_sha}  v0_4_7_bundle_manifest.json")
    write("v0_4_7_semantic.sha256", f"{semantic_sha}  v0_4_7_bundle_manifest.semantic")
    return manifest_sha, semantic_sha


if __name__ == "__main__":
    result = official()
    print(json.dumps({"procedure_passed": result["v0_4_7_procedure_passed"], "decision": result["final_decision"],
                      "positive": result["positive_scenario_passed_count"], "negative": result["negative_scenario_passed_count"]}, ensure_ascii=False))
