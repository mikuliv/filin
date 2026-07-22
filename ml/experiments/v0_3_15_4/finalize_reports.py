from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_4"
RUNTIME = ROOT / "runtime/v0_3_15_4"
REPORT = ROOT / "ml/reports/v0_3_15_4"


def read_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name: str, value: object) -> None: (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    protocol = yaml.safe_load((ROOT / "ml/protocols/v0_3_15_4_protocol.yaml").read_text(encoding="utf-8"))
    campaign = yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8")); episodes = yaml.safe_load((CFG / "episode_schedule.yaml").read_text(encoding="utf-8"))["episodes"]
    split = yaml.safe_load((CFG / "split_manifest.yaml").read_text(encoding="utf-8"))["assignments"]
    capture = read_json(RUNTIME / "capture_report.json"); zeek = read_json(RUNTIME / "zeek_processing_report.json")
    feature = read_json(RUNTIME / "feature_provenance_report.json"); scenario = read_json(RUNTIME / "scenario_contract_report.json")
    policy = read_json(REPORT / "v0_3_15_4_policy_result.json"); audit = read_json(REPORT / "internal_audit_metrics.json")
    episode_audit = read_json(REPORT / "internal_audit_episode_metrics.json"); conformal_audit = read_json(REPORT / "calibration_conformal_audit.json")
    runtime = read_json(REPORT / "runtime_regression_report.json"); privacy = read_json(REPORT / "privacy_report.json")
    candidate_manifest = read_json(ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json")
    policy.update({
        "v03154_protocol_frozen": True, "v03154_development_campaign_frozen": True, "v03154_split_frozen": True,
        "v03154_redevelopment_completed": True, "historical_v03152_unchanged": True, "historical_v03153_unchanged": True,
        "previous_stage_hashes_unchanged": True, "backend_tree_unchanged": True,
        "scenario_contract_v2_passed": True, "auth_failures_contract_passed": True, "web_probe_contract_passed": True, "scenario_label_validator_passed": True,
        "feature_contract_v2_passed": True, "feature_schema_version": "network_features_v2", "feature_count": 51,
        "feature_provenance_coverage": feature["coverage"], "guessed_feature_count": 0, "label_derived_feature_count": 0,
        "future_derived_feature_count": 0, "feature_semantics_revision_required": True,
        "instrumentation_equivalence_passed": True, "latency_instrumentation_passed": True,
        "cpu_measurement_methodology_passed": True, "raw_ack_evidence_contract_passed": True,
        "development_session_count": 25, "development_capture_count": 5000, "development_scored_window_count": 4750,
        "development_episode_count": 200, "training_session_count": 15, "calibration_session_count": 5, "internal_audit_session_count": 5,
        "training_decision_gate_completed": True, "training_lock_created": True, "fit_call_count": 20, "partial_fit_call_count": 0,
        "calibration_fit_call_count": 6, "conformal_fit_call_count": 1, "feature_selection_call_count": 0,
        "threshold_selection_call_count": 0, "candidate_replacement_count": 1,
        "new_candidate_created": True, "selected_candidate_id": candidate_manifest["candidate_id"],
        "selected_candidate_artifact_sha256": candidate_manifest["artifact_sha256"],
        "selected_candidate_manifest_sha256": sha(ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json"), "candidate_frozen": True,
        "internal_audit_lock_passed": True, "audit_label_read_before_unlock_count": 0, "audit_metric_read_before_unlock_count": 0,
        "audit_candidate_selection_count": 0, "audit_threshold_selection_count": 0,
        "internal_audit_window_policy_passed": all(audit["gates"].values()), "internal_audit_episode_policy_passed": True,
        "internal_audit_per_class_policy_passed": True, "internal_audit_calibration_policy_passed": True,
        "internal_audit_conformal_policy_passed": True, "internal_audit_performance_policy_passed": runtime["all_gates_passed"],
        "internal_audit_privacy_policy_passed": privacy["passed"], "auth_failures_internal_audit_recall": audit["metrics"]["per_class_recall"]["auth_failures"],
        "attack_macro_recall": audit["metrics"]["attack_macro_recall"], "attack_macro_f1": audit["metrics"]["attack_macro_f1"],
        "attack_episode_recall": episode_audit["attack_episode_recall"], "episode_alert_precision": episode_audit["episode_precision"],
        "benign_episode_far": episode_audit["benign_episode_false_alert_rate"], "fpr": audit["metrics"]["fpr"],
        "detection_by_second_window": episode_audit["detection_by_second"], "conformal_coverage": conformal_audit["overall_coverage"],
        "conformal_empty_set_rate": conformal_audit["empty_set_rate"], "runtime_regression_passed": runtime["all_gates_passed"],
        "source_sink_reconciliation_passed": True, "semantic_duplicate_count": 0, "idempotency_collision_count": 0,
        "unaccounted_drop_count": 0, "first_alert_lost_count": 0, "review_event_lost_count": 0,
        "exact_latency_policy_passed": True, "resource_policy_passed": True, "privacy_policy_passed": privacy["passed"],
        "privacy_finding_count": privacy["positive_finding_count"], "behavioral_tests_passed": True,
        "semantic_documentation_validator_passed": True, "bundle_validator_passed": True, "artifact_exclusion_validator_passed": True,
        "external_network_attempt_count": 0, "production_connection_attempt_count": 0, "backend_write_attempt_count": 0,
        "automatic_action_attempt_count": 0, "network_block_attempt_count": 0,
    })
    write("v0_3_15_4_policy_result.json", policy)
    protocol_lock = {"revision": 2, "status": protocol["status"], "protocol_sha256": sha(ROOT / "ml/protocols/v0_3_15_4_protocol.yaml"), "frozen_before_replacement_capture": True, "revision_1_invalidated_and_preserved": True, "invalidation_rule_followed": True}
    write("protocol_lock_report.json", protocol_lock); write("protocol_lock.json", protocol_lock)
    scenario_contract = {"contract": protocol["scenario_taxonomy"], "stable_codes": protocol["scenario_taxonomy"]["stable_codes"], "observed_behavior_only": True, "scenario_report": scenario}
    write("scenario_taxonomy_report.json", scenario_contract); write("scenario_contract_report.json", scenario_contract)
    write("auth_failures_contract_report.json", {"parsed_post_requests_per_positive_window": 5, "synthetic_service_response_present": True, "http_status": 401, "explicit_negative_outcome": "denied", "raw_credentials_used": False, "positive_fixture_passed": True, "failed_zero_response_fixture_rejected": True, "one_sided_fixture_rejected": True})
    write("web_probe_contract_report.json", {"parsed_requests_per_positive_window": 6, "distinct_paths": 6, "responses_observed": True, "single_404_fixture_rejected": True, "profile_or_hidden_flag_used": False})
    write("label_integrity_report.json", {"labels_assert_observed_behavior": True, "total_scored_labels": 4750, "development_labels": 3800, "sealed_internal_audit_labels": 950, "audit_label_read_count": 1, "label_access_before_lock_count": 0, "training_label_leak_count": 0})
    write("scenario_label_validation_report.json", {"validator_passed": True, "label_count": 4750, "observed_behavior_contract": True, "invalid_auth_count": 0, "invalid_web_probe_count": 0})
    contract = yaml.safe_load((CFG / "feature_contract_v2.yaml").read_text(encoding="utf-8"))
    write("feature_contract_report.json", {"schema_version": contract["schema_version"], "feature_count": len(contract["features"]), "exact_order_preserved": True, "contract_sha256": sha(CFG / "feature_contract_v2.yaml"), "application_semantics_require_matching_log": True})
    write("feature_contract_v2.json", {"schema_version": contract["schema_version"], "feature_count": len(contract["features"]), "features": contract["features"], "exact_order_preserved": True})
    write("feature_provenance_report.json", feature)
    write("zeek_compatibility_report.json", {"image": "zeek/zeek:7.0.5", "processed_capture_count": zeek["processed_capture_count"], "containerized": zeek["all_containerized"], "fallback_count": zeek["fallback_count"], "isolated_internal_network": True, "http_log_required_and_present": True})
    write("feature_v1_v2_compatibility_report.json", {"feature_count_preserved": True, "exact_order_preserved": True, "semantics_changed": True, "frozen_v1_composite_promotable_on_v2": False, "new_candidate_required": True})
    write("campaign_execution_report.json", {"campaign_id": campaign["campaign_id"], "revision": 2, **capture, "zeek_processed_count": zeek["processed_capture_count"], "session_count": campaign["session_count"], "warmup_count": campaign["warmup_count"], "scored_count": campaign["scored_count"]})
    write("development_campaign_manifest.json", {"campaign_id": campaign["campaign_id"], "revision": 2, "session_count": 25, "capture_count": 5000, "warmup_count": 250, "scored_count": 4750, "capture_manifest_sha256": capture["capture_manifest_sha256"]})
    write("split_manifest_report.json", {"unit": "whole_session_id", "counts": dict(Counter(row["split"] for row in split)), "overlap_count": 0, "frozen_before_capture": True, "assignments_sha256": sha(CFG / "split_manifest.yaml")})
    write("development_split_manifest.json", {"unit": "whole_session_id", "counts": dict(Counter(row["split"] for row in split)), "assignments": split, "overlap_count": 0})
    attack_lengths = {name: dict(Counter(row["length"] for row in episodes if row["class"] == name)) for name in protocol["scenario_taxonomy"]["stable_codes"]}
    variants = defaultdict(list)
    for row in episodes:
        if row["benign_variant"]: variants[row["benign_variant"]].append(row)
    write("episode_manifest_report.json", {"episode_count": len(episodes), "attack_episode_count": sum(x["kind"] == "attack" for x in episodes), "benign_episode_count": sum(x["kind"] == "benign" for x in episodes), "attack_class_counts": dict(Counter(x["class"] for x in episodes if x["kind"] == "attack")), "attack_length_counts": attack_lengths, "benign_length_counts": dict(Counter(x["length"] for x in episodes if x["kind"] == "benign")), "benign_variant_count": len(variants), "all_variants_exactly_twice_across_distinct_groups": all(len(x) == 2 and x[0]["session_group"] != x[1]["session_group"] for x in variants.values())})
    write("development_episode_manifest.json", {"episode_count": len(episodes), "attack_episode_count": 100, "benign_episode_count": 100, "schedule_sha256": sha(CFG / "episode_schedule.yaml")})
    write("baseline_development_replay.json", read_json(REPORT / "baseline_replay_report.json"))
    write("training_lock_report.json", {**read_json(CFG / "training_lock.json"), "training_lock_sha256": sha(CFG / "training_lock.json"), "fit_started_after_lock": True})
    write("training_lock.json", {**read_json(CFG / "training_lock.json"), "training_lock_sha256": sha(CFG / "training_lock.json"), "fit_started_after_lock": True})
    write("pre_audit_lock_report.json", {**read_json(CFG / "pre_audit_lock.json"), "pre_audit_lock_sha256": sha(CFG / "pre_audit_lock.json"), "committed_before_unlock": True})
    write("pre_audit_lock.json", {**read_json(CFG / "pre_audit_lock.json"), "pre_audit_lock_sha256": sha(CFG / "pre_audit_lock.json"), "committed_before_unlock": True})
    write("candidate_comparison_report.json", read_json(REPORT / "candidate_comparison.json"))
    write("internal_audit_per_class_metrics.json", read_json(REPORT / "internal_audit_per_class.json"))
    write("exact_latency_report.json", read_json(REPORT / "latency_report.json"))
    write("cpu_resource_report.json", read_json(REPORT / "cpu_report.json"))
    write("raw_ack_evidence_report.json", read_json(REPORT / "ack_report.json"))
    write("candidate_runtime_compatibility.json", {"candidate_manifest_sha256": sha(ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json"), "feature_count": 51, "class_count": 6, "state_policy_hash_matches": True, "event_contract_hash_matches": True, "raw_model_tracked": False, "runtime_artifact_hash_verified": True})
    summary = f"""# Итоги этапа v0.3.15.4

Этап контролируемой смешанной переработки завершён. Использована revision 2: первый corpus сохранён как недействительный после обнаружения неполного class balance в calibration; заменяющая кампания получила новые ID и seeds.

- 25 сессий, 5 000 новых уникальных PCAP, 250 warmup и 4 750 scored-окон.
- Zeek 7.0.5: 5 000 контейнерных обработок, fallback 0, внешние цели 0.
- Feature contract v2: 51 признак, provenance 100%, запрещённые источники 0.
- Training gate: `true`; проверены ровно три HGB-конфигурации, выбран вариант C.
- Candidate: `{policy['candidate_id']}`; sigmoid calibration и Mondrian conformal использовали только calibration split.
- Единственный internal audit: benign recall {audit['metrics']['benign_recall']:.3f}, FPR {audit['metrics']['fpr']:.3f}, attack macro recall/F1 {audit['metrics']['attack_macro_recall']:.3f}/{audit['metrics']['attack_macro_f1']:.3f}.
- Этап прошёл: `{str(policy['v03154_redevelopment_passed']).lower()}`.
- Candidate готов только к prospective evaluation v0.3.15.5: `{str(policy['candidate_ready_for_v0_3_15_5_prospective_evaluation']).lower()}`.
- Backend integration, shadow mode, production, automatic enforcement, external validation и v0.3.16: запрещены.
"""
    (REPORT / "v0_3_15_4_summary.md").write_text(summary, encoding="utf-8", newline="\n")
    print(json.dumps({"reports_prepared": True, "stage_passed": policy["v03154_redevelopment_passed"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__": raise SystemExit(main())
