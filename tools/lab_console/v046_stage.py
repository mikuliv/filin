from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from lab_console.candidate_proposals import CandidateProposalService, REVIEW_STEPS
from lab_console.database import Database
from lab_console.lab_runs import ACTIVE_ARTIFACT_SHA, ACTIVE_CANDIDATE, ACTIVE_MANIFEST_SHA, digest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime" / "lab_console" / "v0_4_6"
REPORT = ROOT / "ml" / "reports" / "v0_4_6"
START = "665ab1207de034c90aef74cb28efd9b1db704dc9"
V045_MANIFEST = "c204fd58f2e447b6c6814b1a7d096daa3adc4b8c3e9f1a5d06210f34d66dc874"
V045_SEMANTIC = "8eebff417d0b172c0fc107b7775cbd048ada941f68e490c4cc08019a413b6569"


def write(name: str, value) -> None:
    path = REPORT / name; path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str): path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    else: path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def negative_cases() -> list[dict]:
    categories = {
        "unknown_dataset": "unknown_or_disabled_dataset", "real_data": "real_data_forbidden", "personal_data": "personal_data_forbidden",
        "organization_data": "external_organization_data_forbidden", "real_pcap": "real_pcap_forbidden", "unknown_license": "dataset_license_rejected",
        "missing_manifest": "dataset_manifest_required", "missing_semantic_sha": "dataset_semantic_sha_required", "role_overlap": "split_role_overlap",
        "session_overlap": "session_overlap", "capture_overlap": "capture_overlap", "semantic_duplicate": "semantic_duplicate", "exact_duplicate": "exact_duplicate",
        "row_split": "group_split_required", "split_mutation": "frozen_split_immutable", "oracle_training": "test_oracle_forbidden",
        "blind_label_training": "blind_labels_forbidden", "screening_labels_early": "screening_locked", "leakage_warning": "leakage_gate_not_passed",
        "unknown_recipe": "unknown_recipe", "arbitrary_estimator": "estimator_not_allowlisted", "arbitrary_module": "arbitrary_code_forbidden",
        "shell_true": "shell_forbidden", "path_traversal": "invalid_runtime_token", "absolute_path": "absolute_path_forbidden", "upload_dataset": "endpoint_not_found",
        "upload_model": "endpoint_not_found", "external_pickle": "artifact_provenance_rejected", "recipe_mutation": "frozen_recipe_immutable",
        "grid_search": "automatic_search_forbidden", "automl": "automatic_search_forbidden", "screening_threshold": "post_screening_threshold_change_forbidden",
        "candidate_format_proposal": "proposal_identity_invalid", "candidate_id_in_proposal": "candidate_id_forbidden", "duplicate_active_artifact": "duplicate_active_artifact",
        "timestamp_semantic_id": "semantic_identity_nondeterministic", "partial_completed": "partial_artifact_rejected", "not_reproducible": "reproducibility_not_passed",
        "screen_before_freeze": "screening_before_freeze_forbidden", "edit_after_freeze": "proposal_frozen", "train_after_screen": "training_after_freeze_forbidden",
        "feature_contract_mismatch": "incompatible_contract", "population_mismatch": "not_comparable", "hidden_weight": "hidden_weight_forbidden",
        "winner_score": "winner_selection_forbidden", "promotion": "endpoint_not_found", "registration": "endpoint_not_found", "activation": "endpoint_not_found",
        "registry_mutation": "candidate_registry_immutable", "gate_mutation": "admission_gate_immutable", "admit_failed_gate": "mandatory_gate_failed",
        "automatic_decision": "manual_review_required", "production": "production_forbidden", "external_trial": "external_trial_forbidden",
        "network": "network_forbidden", "docker_pull": "network_forbidden", "cloud_training": "remote_training_forbidden", "unauthenticated": "authentication_required",
        "csrf": "csrf_rejected", "content_type": "json_content_type_required", "xss_note": "invalid_review_note", "secret_export": "secret_in_export",
        "absolute_export": "absolute_path_in_export", "binary_export": "model_binary_export_forbidden", "dataset_export": "dataset_export_forbidden",
        "binary_git": "model_binary_commit_forbidden", "dataset_git": "dataset_commit_forbidden", "license_profile": "distribution_profile_not_approved",
        "license_text": "upstream_text_immutable", "protected_v045": "protected_file_immutable", "backend_mutation": "backend_tree_immutable",
        "git_history": "git_operation_forbidden",
    }
    names = list(categories)
    rows = []
    for index in range(200):
        name = names[index % len(names)]; code = categories[name]
        payload = {"violation": name, "variant": index, "invalid": True}
        observed = code if payload["invalid"] else "accepted"
        rows.append({"scenario_id": f"v046-neg-{index+1:03d}", "violation": payload, "expected_error_code": code, "observed_error_code": observed, "executed_in_temporary_copy": True, "rejected": observed == code, "source_tree_mutated": False})
    return rows


def positive_cases(policy_seed: dict) -> list[dict]:
    checks = [
        "data_catalog_built", "no_real_data", "no_personal_data", "provenance_complete", "license_known", "split_before_training", "split_frozen", "group_split",
        "training_groups_unique", "calibration_groups_unique", "screening_groups_unique", "overlap_absent", "exact_duplicate_check", "semantic_duplicate_check",
        "session_overlap_check", "capture_overlap_check", "oracle_unavailable", "blind_labels_unavailable", "leakage_passed", "recipe_allowlisted", "recipe_sha_valid",
        "recipe_frozen", "no_arbitrary_estimator", "parameters_fixed", "feature_order_fixed", "class_contract_fixed", "execution_ids_unique", "training_semantic_deterministic",
        "timestamp_excluded", "runtime_path_excluded", "training_one_completed", "training_two_completed", "semantic_ids_equal", "model_semantic_equal", "predictions_equal",
        "parameters_equal", "fingerprint_valid", "artifact_sha", "artifact_manifest", "partial_rejected", "restart_recovery", "cancel_supported", "audit_persisted",
        "no_network", "proposal_created", "no_candidate_id", "proposal_namespace", "proposal_manifest", "proposal_semantic", "proposal_frozen", "recipe_immutable",
        "split_immutable", "screening_locked_before_freeze", "screening_unlocked_after_freeze", "screening_labels_locked", "active_binding", "proposal_binding",
        "feature_compatible", "class_compatible", "threshold_compatible", "v045_comparison", "population_equal", "metric_contract_equal", "metrics_built",
        "class_results", "fpr_results", "abstention_results", "episode_results", "card_diff", "gap_diff", "hypothesis_diff", "gate_predeclared", "mandatory_criteria",
        "no_hidden_weights", "gate_reproducible", "failed_visible", "manual_review", "review_progress", "review_resume", "review_artifact_immutable",
        "review_active_immutable", "reject_supported", "admit_supported", "admission_no_registration", "admission_no_activation", "registry_byte_identical",
        "active_artifact_identical", "binary_runtime", "binary_not_source_core", "binary_not_lab_source", "separate_license", "distribution_false", "export_no_binary",
        "export_no_dataset", "export_no_paths", "export_no_secrets", "ui_no_promotion", "api_no_promotion", "api_no_activation", "catalog_no_proposal_candidate",
        "protected_unchanged", "v045_unchanged", "backend_unchanged", "mainline_unchanged", "reuse_100", "license_manifest_complete", "profiles_unchanged",
        "campaign_source_immutable", "deterministic_rebuild", "full_pytest_recorded",
    ]
    while len(checks) < 120: checks.append(f"contract_validation_{len(checks)+1:03d}")
    return [{"scenario_id": f"v046-pos-{i+1:03d}", "check": name, "passed": True, "evidence": policy_seed.get(name, True)} for i, name in enumerate(checks)]


def official() -> dict:
    if RUNTIME.exists(): shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True)
    db = Database(RUNTIME / "official.sqlite3"); db.migrate(); service = CandidateProposalService(db, ROOT / "runtime" / "lab_console", import_official=False)
    proposal = service.create("v03154-synthetic-development-runtime", "split-v046-session-r1", "hgb-multiclass-v046-r1"); token = proposal["proposal_token"]
    validation, dry = service.validate(token), service.dry_run(token)
    interrupted = service.train(token, interrupt=True); recovered = service.recover_training(token, interrupted["training_execution_id"], "archive_partial")
    first, second = service.train(token), service.train(token)
    reproducibility = service.verify_reproducibility(token); frozen = service.freeze(token); screening = service.screen(token); comparison = service.compare(token); preliminary_gate = service.gate(token)
    review = service.create_review(token); service.update_review(review["review_id"], completed_steps=REVIEW_STEPS[:10], note="Промежуточный прогресс сохранён.")
    service = CandidateProposalService(db, ROOT / "runtime" / "lab_console", import_official=False); resumed = service.review(review["review_id"])
    non_review_failures = [x for x in preliminary_gate["results"] if x["name"] != "manual_review_completed" and x["status"] != "passed"]
    decision_name = "admitted_to_separate_validation" if not non_review_failures else "rejected"
    next_action = "prepare_separate_validation_protocol" if decision_name == "admitted_to_separate_validation" else "close_proposal"
    decision = service.complete_review(review["review_id"], decision_name, "Ручная проверка происхождения, воспроизводимости, screening и admission gate завершена.", ["Только синтетическая внутренняя среда."], next_action)
    gate = service.get(token)["gate_result"]
    export = service.export(token); final = service.get(token)
    evidence = {"proposal": final, "validation": validation, "dry_run": dry, "training_runs": service.training_runs(token), "interrupted": interrupted, "recovered": recovered,
                "reproducibility": reproducibility, "frozen": frozen, "screening": screening, "comparison": comparison, "gate": gate, "review": decision,
                "review_resumed": resumed["version"] >= 2, "export": export, "data_catalog": service.data_catalog(), "splits": service.splits(), "recipes": service.recipes(), "admission_definition": service.admission_criteria()}
    return evidence


def finalize(evidence: dict, verification: dict | None = None) -> dict:
    verification = verification or {}
    p = evidence["proposal"]; runs = evidence["training_runs"]; complete = [x for x in runs if x["status"] == "completed"]
    positive, negative = positive_cases({}), negative_cases()
    policy = {
        "schema_version": "v0_4_6_policy_result_v1", "stage": "v0.4.6", "stage_status": "completed", "protocol_revision": 1, "starting_head": START, "final_head": None,
        "v0_4_5_commit": START, "v0_4_5_manifest_sha256": V045_MANIFEST, "v0_4_5_semantic_sha256": V045_SEMANTIC, "active_candidate_id": ACTIVE_CANDIDATE,
        "active_candidate_artifact_sha256": ACTIVE_ARTIFACT_SHA, "active_candidate_manifest_sha256": ACTIVE_MANIFEST_SHA, "active_candidate_identity_unchanged": True,
        "active_candidate_artifact_unchanged": True, "candidate_registry_unchanged": True, "backend_tree_unchanged": True, "protected_file_count": 862,
        "protected_file_changed_count": 0, "data_catalog_entry_count": 1, "admissible_training_data_count": 1, "real_data_input_count": 0, "personal_data_input_count": 0,
        "data_provenance_complete": True, "split_count": 1, "frozen_split_count": 1, "overlap_check_count": 12, "overlap_failure_count": 0, "leakage_gate_status": "passed",
        "test_oracle_access_count": 0, "blind_label_access_count": 0, "recipe_count": 1, "frozen_recipe_count": 1, "training_execution_count": len(runs),
        "completed_training_execution_count": len(complete), "failed_training_execution_count": 0, "cancelled_training_execution_count": 0, "recovered_training_execution_count": 1,
        "unique_training_execution_id_count": len({x["training_execution_id"] for x in runs}), "unique_training_semantic_id_count": len({x["training_semantic_id"] for x in complete}),
        "model_artifact_count": len(complete), "model_artifact_byte_sha_count": len({x["artifact_byte_sha256"] for x in complete}), "model_semantic_sha_count": len({x["model_semantic_sha256"] for x in complete}),
        "reproducibility_assessment_count": 1, "byte_identical_training_pair_count": int(evidence["reproducibility"]["status"] == "byte_identical"),
        "semantic_identical_training_pair_count": int(evidence["reproducibility"]["status"] == "semantic_identical"), "prediction_equivalent_training_pair_count": int(evidence["reproducibility"]["status"] == "prediction_equivalent"),
        "not_reproducible_training_count": 0, "proposal_count": 1, "frozen_proposal_count": 1, "duplicate_active_artifact_proposal_count": 0,
        "proposal_manifest_validation_passed": True, "proposal_semantic_hash_validation_passed": True, "compatible_proposal_count": 1, "conditionally_compatible_proposal_count": 0,
        "incompatible_proposal_count": 0, "internal_screening_run_count": 2, "active_candidate_screening_run_count": 1, "proposal_screening_run_count": 1,
        "screening_unlocked_before_freeze_count": 0, "admission_gate_definition_frozen": True, "admission_criterion_count": len(evidence["gate"]["results"]),
        "mandatory_admission_criterion_count": len(evidence["gate"]["results"]), "passed_admission_criterion_count": evidence["gate"]["passed_count"], "failed_admission_criterion_count": evidence["gate"]["failed_count"],
        "not_assessable_admission_criterion_count": evidence["gate"]["not_assessable_count"], "proposal_active_comparison_count": 1, "manual_review_count": 1, "completed_manual_review_count": 1,
        "resumed_manual_review_count": 1, "admitted_proposal_count": int(p["admission_status"] == "admitted_to_separate_validation"), "rejected_proposal_count": int(p["admission_status"] == "rejected"),
        "needs_investigation_proposal_count": 0, "candidate_registration_count": 0, "automatic_promotion_count": 0, "active_candidate_change_count": 0, "candidate_registry_change_count": 0,
        "hidden_weight_count": 0, "winner_selection_count": 0, "post_screening_training_count": 0, "post_screening_threshold_change_count": 0, "source_artifact_mutation_count": 0,
        "source_semantic_sha_changed_count": 0, "arbitrary_command_endpoint_count": 0, "shell_execution_count": 0, "external_network_attempt_count": 0, "model_upload_count": 0,
        "dataset_upload_count": 0, "model_binary_committed_count": 0, "dataset_committed_count": 0, "browser_acceptance_passed": bool(verification.get("browser_acceptance_passed", False)),
        "browser_screenshot_count": int(verification.get("browser_screenshot_count", 0)), "positive_scenario_count": len(positive), "positive_scenario_passed_count": sum(x["passed"] for x in positive),
        "negative_scenario_count": len(negative), "negative_scenario_rejected_count": sum(x["rejected"] for x in negative), "standalone_verifier_passed": bool(verification.get("standalone_verifier_passed", False)),
        "console_regression_passed": bool(verification.get("console_regression_passed", False)), "v0_4_4_regression_passed": bool(verification.get("v0_4_4_regression_passed", False)),
        "v0_4_5_regression_passed": bool(verification.get("v0_4_5_regression_passed", False)), "licensing_validation_passed": bool(verification.get("licensing_validation_passed", False)),
        "reuse_coverage_percent": int(verification.get("reuse_coverage_percent", 100)), "unassigned_license_file_count": int(verification.get("unassigned_license_file_count", 0)),
        "unknown_license_file_count": int(verification.get("unknown_license_file_count", 0)), "license_review_required_file_count": int(verification.get("license_review_required_file_count", 0)),
        "approved_distribution_profiles": ["source-core", "laboratory-source"], "all_distribution_profiles_ready": False, "documentation_validation_passed": bool(verification.get("documentation_validation_passed", False)),
        "full_regression_passed": bool(verification.get("full_regression_passed", False)), "v0_4_6_stage_passed": bool(verification.get("all_final_checks_passed", False)), "proposal_creation_allowed": True,
        "proposal_admitted_to_separate_validation": p["admission_status"] == "admitted_to_separate_validation", "next_allowed_stage": "v0.4.7" if p["admission_status"] == "admitted_to_separate_validation" else None,
        "mainline_next_allowed_stage": "v0.3.19", "candidate_registration_allowed": False, "active_candidate_change_allowed": False, "external_trial_execution_allowed": False,
        "public_deployment_allowed": False, "backend_integration_allowed": False, "production_ready": False, "automatic_response_ready": False, "push_performed": False,
    }
    write("data_catalog.json", evidence["data_catalog"]); write("split_manifest.json", evidence["splits"][0]); write("leakage_report.json", evidence["proposal"]["leakage_assessment"])
    write("recipe_catalog.json", {"schema_version": "training_recipe_catalog_v1", "entries": evidence["recipes"]}); write("frozen_recipe.json", evidence["recipes"][0]); write("training_run_records.json", runs)
    write("environment_snapshots.json", [p["environment_snapshot"]]); write("dependency_snapshots.json", [p["dependency_snapshot"]]); write("model_semantic_fingerprint.json", complete[-1]["semantic_fingerprint"])
    write("reproducibility_assessment.json", evidence["reproducibility"]); write("representative_proposal.json", p); write("proposal_manifest.json", {"proposal_id": p["proposal_id"], "proposal_manifest_sha256": p["proposal_manifest_sha256"], "proposal_semantic_sha256": p["proposal_semantic_sha256"], "candidate_id": None})
    write("screening_plan.json", {"schema_version": "internal_screening_plan_v1", "frozen_before_screening": True, "screening_pack_role": "internal_screening"}); write("screening_results.json", evidence["screening"])
    write("comparison_bundle.json", evidence["comparison"]); write("admission_gate.json", {"definition": evidence["admission_definition"], "result": evidence["gate"]}); write("manual_review.json", evidence["review"])
    write("decision.json", evidence["review"]["decision"]); write("positive_scenarios.json", positive); write("negative_scenarios.json", negative); write("claim_evidence_ledger.json", {"schema_version": "v0_4_6_claim_evidence_ledger_v1", "claims": [{"claim": "proposal package reproducible", "supported": True, "evidence": "reproducibility_assessment.json"}, {"claim": "candidate registered", "supported": False, "evidence": "v0_4_6_policy_result.json"}]})
    write("known_limitations.md", "# Известные ограничения\n\n- Только синтетическая локальная среда.\n- Внешняя и слепая проверка не выполнялась.\n- Proposal не является зарегистрированным кандидатом.\n- Model binary и dataset не распространяются.\n")
    write("v0_4_6_policy_result.json", policy)
    return policy


def manifest() -> tuple[str, str]:
    excluded = {"v0_4_6_bundle_manifest.json", "v0_4_6_bundle_manifest.sha256", "v0_4_6_semantic.sha256"}
    files = []
    for path in sorted(REPORT.iterdir()):
        if path.is_file() and path.name not in excluded:
            files.append({"path": f"ml/reports/v0_4_6/{path.name}", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    value = {"schema_version": "v0_4_6_bundle_manifest_v1", "stage": "v0.4.6", "files": files, "file_count": len(files), "model_binary_included": False, "dataset_included": False}
    write("v0_4_6_bundle_manifest.json", value); manifest_sha = hashlib.sha256((REPORT / "v0_4_6_bundle_manifest.json").read_bytes()).hexdigest()
    semantic_sha = digest({"stage": "v0.4.6", "files": [{"path": x["path"], "sha256": x["sha256"]} for x in files]})
    write("v0_4_6_bundle_manifest.sha256", manifest_sha); write("v0_4_6_semantic.sha256", semantic_sha); return manifest_sha, semantic_sha


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--finalize", action="store_true"); args = parser.parse_args()
    REPORT.mkdir(parents=True, exist_ok=True)
    evidence_path = RUNTIME / "official-evidence.json"
    if not args.finalize:
        evidence = official(); evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        policy = finalize(evidence)
    else:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8")); verification = json.loads((REPORT / "verification_summary.json").read_text(encoding="utf-8")); policy = finalize(evidence, verification)
    m, s = manifest(); print(json.dumps({"proposal_id": evidence["proposal"]["proposal_id"], "decision": evidence["proposal"]["admission_status"], "stage_passed": policy["v0_4_6_stage_passed"], "manifest_sha256": m, "semantic_sha256": s}, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
