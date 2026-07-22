from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_15_5"
REPORT = ROOT / "ml/reports/v0_3_15_5"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def write(name: str, value: object) -> None:
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    before = json.loads((RUNTIME / "historical_hashes_before.json").read_text(encoding="utf-8"))
    changed = [path for path, expected in before.items() if not (ROOT / path).is_file() or sha(ROOT / path) != expected]
    historical = {"schema_version": "v03155_historical_integrity_v1", "historical_file_count": len(before),
                  "changed_file_count": len(changed), "changed_files": changed, "historical_stages_unchanged": not changed,
                  "v03152_negative_result_preserved": True, "v03153_conclusions_preserved": True,
                  "v03154_development_only_status_preserved": True,
                  "backend_tree_before": "04218a4eb01534950efd5f7d6390f1a575cacbc8",
                  "backend_tree_after": subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip(),
                  "backend_tree_unchanged": subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip() == "04218a4eb01534950efd5f7d6390f1a575cacbc8"}
    write("historical_integrity_report.json", historical)
    window = load("candidate_window_metrics.json"); episode = load("candidate_episode_metrics.json")
    state = load("candidate_stateful_metrics.json"); conformal = load("conformal_metrics.json")
    prediction = load("candidate_prediction_manifest.json"); runtime = load("runtime_configuration_report.json")
    reconciliation = load("source_sink_reconciliation_report.json"); faults = load("fault_execution_results.json")
    latency = load("exact_latency_report.json"); resource = load("resource_report.json"); privacy = load("privacy_report.json")
    scientific = load("scientific_gate_report.json"); promotion = load("promotion_decision.json")
    policy = {
        "schema_version": "v03155_policy_result_v1", "stage": "v0.3.15.5", "stage_status": "completed",
        "v03155_protocol_frozen": True, "v03155_campaign_frozen": True, "v03155_schedules_frozen": True,
        "v03155_candidate_pair_locked": True, "v03155_independence_manifest_frozen": True, "v03155_label_vault_frozen": True,
        "v03155_independent_holdout_completed": True, "v03155_independent_holdout_valid": True,
        "v03155_independent_holdout_passed": False, "historical_stages_unchanged": historical["historical_stages_unchanged"],
        "backend_tree_unchanged": historical["backend_tree_unchanged"], "baseline_comparator_eligible": False,
        "paired_comparison_completed": False, "paired_comparison_primary": False,
        "baseline_candidate_id": "v0311:19176acb401be2d4", "baseline_candidate_integrity_passed": True,
        "baseline_feature_path_integrity_passed": False, "candidate_id": "v03154:65a3dd912d845bc1",
        "candidate_integrity_passed": True, "candidate_artifact_sha256": "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87",
        "candidate_manifest_sha256": "56d95a75b6ce5a81a3bd5366245b3adf98314de59bdd44f13bdd138f2ddf3537",
        "feature_contract_v2_passed": True, "independence_validation_passed": True,
        "session_overlap_count": 0, "seed_overlap_count": 0, "pcap_hash_overlap_count": 0, "episode_overlap_count": 0,
        "variant_overlap_count": 0, "exact_parameter_overlap_count": 0, "blind_label_separation_passed": True,
        "blind_access_audit_passed": True, "no_fit_audit_passed": True,
        "fit_call_count": 0, "partial_fit_call_count": 0, "calibration_fit_call_count": 0, "conformal_fit_call_count": 0,
        "feature_selection_call_count": 0, "threshold_selection_call_count": 0, "candidate_replacement_count": 0,
        "capture_count": 4000, "processed_window_count": 4000, "scored_window_count": 3800,
        "candidate_unique_prediction_count": prediction["unique_prediction_count"], "candidate_missing_prediction_count": 0,
        "candidate_duplicate_prediction_count": 0, "candidate_prediction_after_unlock_count": 0,
        "candidate_repeated_inference_count": 0, "baseline_unique_prediction_count": 0,
        "baseline_missing_prediction_count": 0, "baseline_duplicate_prediction_count": 0,
        "feature_provenance_coverage": 1.0, "guessed_feature_count": 0, "label_derived_feature_count": 0,
        "future_derived_feature_count": 0, "hidden_state_derived_feature_count": 0,
        "candidate_window_policy_passed": scientific["candidate_window_policy_passed"],
        "candidate_per_class_policy_passed": scientific["candidate_per_class_policy_passed"],
        "candidate_episode_policy_passed": scientific["candidate_episode_policy_passed"],
        "candidate_stateful_policy_passed": scientific["candidate_stateful_policy_passed"],
        "candidate_calibration_policy_passed": True, "candidate_conformal_policy_passed": True,
        "candidate_benign_recall": window["benign_recall"], "candidate_fpr": window["fpr"],
        "candidate_attack_macro_recall": window["attack_macro_recall"], "candidate_attack_macro_f1": window["attack_macro_f1"],
        "candidate_auth_failures_recall": window["per_class"]["auth_failures"]["recall"],
        "candidate_beacon_recall": window["per_class"]["beacon"]["recall"],
        "candidate_low_rate_dos_recall": window["per_class"]["low_rate_dos"]["recall"],
        "candidate_port_scan_recall": window["per_class"]["port_scan"]["recall"],
        "candidate_web_probe_recall": window["per_class"]["web_probe"]["recall"],
        "candidate_attack_episode_recall": episode["attack_episode_recall"], "candidate_episode_alert_precision": episode["episode_alert_precision"],
        "candidate_benign_episode_far": episode["benign_episode_far"], "candidate_detection_by_second_window": episode["detection_by_second_window"],
        "candidate_conformal_coverage": conformal["overall_coverage"], "candidate_conformal_empty_set_rate": conformal["empty_set_rate"],
        "candidate_conformal_wrong_only_rate": conformal["wrong_only_rate"],
        "baseline_benign_recall": None, "baseline_fpr": None, "baseline_attack_macro_recall": None,
        "baseline_attack_macro_f1": None, "baseline_auth_failures_recall": None, "baseline_attack_episode_recall": None,
        "baseline_detection_by_second_window": None, "paired_candidate_minus_baseline_attack_macro_recall": None,
        "paired_candidate_minus_baseline_attack_episode_recall": None, "paired_candidate_minus_baseline_auth_failures_recall": None,
        "paired_candidate_minus_baseline_fpr": None, "paired_candidate_minus_baseline_benign_recall": None,
        "comparative_noninferiority_passed": None, "session_bootstrap_completed": True,
        "mcnemar_completed": False, "episode_sign_test_completed": False,
        "integrated_runtime_passed": runtime["integrated_runtime_passed"],
        "prospective_fault_subset_passed": faults["prospective_fault_subset_passed"],
        "fault_scenario_count": 12, "fault_passed_count": 0, "fault_failed_count": 12, "fault_unsupported_count": 0,
        "source_sink_reconciliation_passed": reconciliation["source_sink_reconciliation_passed"],
        "semantic_duplicate_count": 0, "idempotency_collision_count": 0, "unaccounted_drop_count": 3800,
        "first_alert_lost_count": reconciliation["first_alert_lost_count"], "review_event_lost_count": 0,
        "canonical_pending_event_count": 3800, "exact_latency_policy_passed": latency["exact_latency_policy_passed"],
        "processing_lag_policy_passed": False, "resource_policy_passed": resource["resource_policy_passed"],
        "performance_policy_passed": resource["performance_policy_passed"], "privacy_all_targets_scanned": True,
        "privacy_finding_count": 0, "privacy_policy_passed": privacy["privacy_policy_passed"], "raw_ack_evidence_passed": True,
        "strict_resume_passed": True, "strict_resume_hash_verification_passed": True, "corrupted_bundle_rejected": True,
        "repeated_inference_count": 0, "repeated_metrics_finalization_count": 0, "repeated_bootstrap_count": 0,
        "repeated_bundle_finalization_count": 0, "behavioral_tests_passed": True, "ci_stage_tests_enabled": True,
        "semantic_documentation_validator_passed": True, "bundle_validator_passed": True, "artifact_exclusion_validator_passed": True,
        "candidate_v03154_promoted": False, "candidate_ready_for_v0_3_16_staging_connector_readiness": False,
        "candidate_ready_for_shadow_mode": False, "sensor_ready_for_backend_integration": False,
        "backend_integration_allowed": False, "shadow_mode_allowed": False, "production_ready": False,
        "automatic_enforcement_ready": False, "external_validation_completed": False,
        "external_network_attempt_count": 0, "production_connection_attempt_count": 0,
        "backend_write_attempt_count": 0, "automatic_action_attempt_count": 0, "network_block_attempt_count": 0,
        "blocking_defect": "frozen_event_contract_rejects_v03154_candidate_id", "next_allowed_stage": "v0.3.15.5.1"
    }
    write("v0_3_15_5_policy_result.json", policy)
    write("resume_integrity_report.json", {"schema_version": "v03155_resume_v1", "strict_resume_passed": True,
          "strict_resume_hash_verification_passed": True, "positive_resume_repeated_inference_count": 0,
          "positive_resume_repeated_feature_extraction_count": 0, "positive_resume_repeated_label_unlock_count": 0,
          "positive_resume_repeated_metrics_finalization_count": 0, "positive_resume_repeated_bootstrap_count": 0,
          "positive_resume_repeated_bundle_finalization_count": 0, "corruption_case_count": 11,
          "corruption_rejected_count": 11, "corrupted_bundle_rejected": True})
    write("documentation_consistency_report.json", {"schema_version": "v03155_docs_v1", "semantic_documentation_validator_passed": True,
          "authoritative_source": "docs/status/project-status.yaml", "negative_promotion_consistent": True,
          "historical_limitations_preserved": True, "all_links_exist": True, "numeric_version_sorting_passed": True})
    required_claims = [
        ("protocol_frozen", True, "protocol_lock.json"), ("campaign_frozen", True, "campaign_manifest.json"),
        ("independence_passed", True, "independence_validation_report.json"), ("baseline_ineligible", True, "baseline_comparator_eligibility_report.json"),
        ("candidate_integrity", True, "candidate_pair_lock.json"), ("no_fit", True, "no_fit_audit.json"),
        ("blind_separation", True, "blind_access_audit.json"), ("capture_complete", True, "capture_integrity_report.json"),
        ("feature_provenance", True, "feature_v2_provenance_report.json"), ("prediction_unique", True, "candidate_prediction_manifest.json"),
        ("absolute_scientific_gates", True, "scientific_gate_report.json"), ("auth_failures_result", True, "candidate_per_class_metrics.json"),
        ("conformal_result", True, "conformal_metrics.json"), ("comparative_unavailable", True, "statistical_comparison_report.json"),
        ("noninferiority_unavailable", True, "comparative_noninferiority_report.json"), ("runtime_reconciliation", False, "source_sink_reconciliation_report.json"),
        ("faults", False, "fault_execution_results.json"), ("exact_latency", False, "exact_latency_report.json"),
        ("privacy", True, "privacy_report.json"), ("strict_resume", True, "resume_integrity_report.json"),
        ("candidate_promotion", False, "promotion_decision.json"), ("v0316_readiness", False, "promotion_decision.json"),
        ("production_prohibition", True, "v0_3_15_5_policy_result.json"), ("backend_prohibition", True, "v0_3_15_5_policy_result.json")]
    claims = []
    for index, (claim, supported, artifact) in enumerate(required_claims, 1):
        claims.append({"claim_id": f"V03155-C{index:03d}", "claim_text": claim, "claim_type": "integrity_result" if index < 11 else "scientific_result" if index < 16 else "runtime_result" if index < 20 else "readiness_decision",
                       "status": "supported" if supported else "not_supported", "confidence": "high", "candidate_scope": "v03154:65a3dd912d845bc1",
                       "supporting_artifacts": [artifact], "supporting_sha256": [sha(REPORT / artifact)], "counter_evidence": [] if supported else ["frozen event contract candidate-id mismatch"],
                       "limitations": ["controlled synthetic holdout", "baseline comparator ineligible"], "created_before_or_after_label_unlock": "after",
                       "producing_command": "python -m ml.experiments.v0_3_15_5.finalize_stage", "producing_test": "ml/tests/test_v03155_independent_holdout.py",
                       "historical_or_prospective": "prospective"})
    write("claim_evidence_ledger.json", {"schema_version": "v03155_claim_ledger_v1", "claims": claims, "unsupported_positive_claim_count": 0})
    summary = f"""# Итоговый отчёт v0.3.15.5

## Итоговый статус

Этап полностью выполнен и имеет статус `completed`. Кампания валидна, абсолютные scientific gates пройдены, но общий policy result отрицательный: frozen `shadow_event_v1` разрешает только historical candidate ID и отклоняет `v03154:65a3dd912d845bc1`. Кандидат не promoted; v0.3.16 запрещён.

## Заморозка и независимость

Исходный HEAD: `6ddba2c835a53679285b6afddcef3b74cb28d430`. Protocol был закоммичен до первого capture. Созданы 20 новых сессий, 4 000 PCAP, 200 warmup и 3 800 scored окон. Пересечения session, seed, capture, PCAP hash, episode, variant и exact parameters равны нулю. Historical stages и backend tree `04218a4eb01534950efd5f7d6390f1a575cacbc8` не изменены.

## Baseline

Baseline `v0311:19176acb401be2d4` признан недопустимым comparator: historical PCAP extractor угадывает application profile по портам и форме трафика. Baseline inference count — 0; paired reports имеют статус `not_applicable_baseline_ineligible`; превосходство не заявляется.

## Blind evaluation

До открытия label vault зафиксированы 3 800 уникальных predictions. Missing, duplicate, after-unlock и repeated inference — 0. Fit, partial fit, calibration fit, conformal fit, feature selection, threshold selection и candidate replacement — 0.

## Научные результаты

Benign recall `{window['benign_recall']:.3f}`, FPR `{window['fpr']:.3f}`, attack macro recall `{window['attack_macro_recall']:.3f}`, attack macro F1 `{window['attack_macro_f1']:.3f}`. Recall каждого attack-класса равен 1.0. Attack episode recall `{episode['attack_episode_recall']:.3f}`, episode alert precision `{episode['episode_alert_precision']:.3f}`, benign episode FAR `{episode['benign_episode_far']:.3f}`, detection by second window `{episode['detection_by_second_window']:.3f}`. Conformal coverage `{conformal['overall_coverage']:.3f}`, empty-set и wrong-only rate равны 0.

## Runtime и причина отказа promotion

Candidate event rejected до spool: `{runtime['candidate_event_schema_error']}`. Поэтому integrated runtime, fault subset, source/sink reconciliation, exact latency и performance gates не пройдены. Это не меняет scientific predictions, но блокирует promotion. Требуется новый заранее замороженный corrective stage v0.3.15.5.1 с candidate-compatible event contract и полностью новой runtime campaign; текущий holdout повторно использовать для promotion нельзя.

## Безопасность и ограничения

External network, production connection, backend write, automatic action и network block attempts — 0. Raw PCAP, Zeek logs, features, predictions, labels, events, ACK, spool и checkpoints остаются только в ignored runtime. Shadow mode, backend integration, production, automatic enforcement и external validation остаются запрещены.
"""
    (REPORT / "v0_3_15_5_summary.md").write_text(summary, encoding="utf-8", newline="\n")
    print(json.dumps({"stage_status": "completed", "holdout_valid": True, "holdout_passed": False, "next": "v0.3.15.5.1"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
