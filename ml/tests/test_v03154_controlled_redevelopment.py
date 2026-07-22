from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "ml/experiments/v0_3_15_4"
REPORT = ROOT / "ml/reports/v0_3_15_4"


def load(name): return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_01_protocol_revision_frozen():
    value=yaml.safe_load((ROOT/"ml/protocols/v0_3_15_4_protocol.yaml").read_text(encoding="utf-8")); assert value["revision"]==2 and value["status"]=="frozen_before_replacement_development_campaign"
def test_02_r1_invalidated_preserved(): assert load("campaign_r1_invalidation.json")["invalidated"] and load("campaign_r1_invalidation.json")["fit_call_count"]==0
def test_03_campaign_shape():
    value=load("campaign_execution_report.json"); assert value["session_count"]==25 and value["capture_count"]==5000 and value["scored_count"]==4750
def test_04_unique_pcaps():
    value=load("campaign_execution_report.json"); assert value["unique_sha256_count"]==5000 and value["all_closed_before_processing"]
def test_05_containerized_zeek():
    value=load("zeek_compatibility_report.json"); assert value["processed_capture_count"]==5000 and value["containerized"] and value["fallback_count"]==0
def test_06_isolated_network(): assert load("zeek_compatibility_report.json")["isolated_internal_network"]
def test_07_split_counts(): assert load("split_manifest_report.json")["counts"]=={"training":15,"calibration":5,"internal_audit":5}
def test_08_split_no_overlap(): assert load("split_manifest_report.json")["overlap_count"]==0
def test_09_episode_counts():
    value=load("episode_manifest_report.json"); assert value["episode_count"]==200 and value["attack_episode_count"]==100 and value["benign_episode_count"]==100
def test_10_attack_balance(): assert set(load("episode_manifest_report.json")["attack_class_counts"].values())=={20}
def test_11_attack_length_balance(): assert all(set(value.values())=={5} for value in load("episode_manifest_report.json")["attack_length_counts"].values())
def test_12_benign_length_balance(): assert set(load("episode_manifest_report.json")["benign_length_counts"].values())=={25}
def test_13_benign_variant_contract():
    value=load("episode_manifest_report.json"); assert value["benign_variant_count"]==50 and value["all_variants_exactly_twice_across_distinct_groups"]
def test_14_auth_observed_contract():
    value=load("auth_failures_contract_report.json"); assert value["parsed_post_requests_per_positive_window"]>=2 and value["synthetic_service_response_present"] and value["http_status"]==401
def test_15_auth_negative_fixtures():
    value=load("auth_failures_contract_report.json"); assert value["failed_zero_response_fixture_rejected"] and value["one_sided_fixture_rejected"]
def test_16_web_observed_contract():
    value=load("web_probe_contract_report.json"); assert value["parsed_requests_per_positive_window"]>1 and value["distinct_paths"]>1 and value["responses_observed"]
def test_17_web_negative_fixture(): assert load("web_probe_contract_report.json")["single_404_fixture_rejected"]
def test_18_feature_count_order():
    value=load("feature_contract_report.json"); assert value["feature_count"]==51 and value["exact_order_preserved"]
def test_19_provenance_coverage():
    value=load("feature_provenance_report.json"); assert value["coverage"]==1 and value["provenance_record_count"]==4750*51
def test_20_no_forbidden_provenance():
    value=load("feature_provenance_report.json"); assert sum(value[key] for key in ["guessed_from_profile_count","guessed_from_label_count","guessed_from_scenario_count","future_inference_count","hidden_state_inference_count"] )==0
def test_21_sidecar_isolation():
    value=load("feature_provenance_report.json"); assert not value["sidecar_used_as_model_input"] and value["label_field_count"]==0 and value["raw_payload_count"]==0
def test_22_training_gate_before_fit():
    value=load("training_necessity_decision.json"); assert value["training_required"] and value["decision_before_first_fit"] and value["fit_call_count_before_lock"]==0
def test_23_training_lock():
    value=load("training_lock_report.json"); assert value["frozen_before_first_fit"] and value["configuration_count"]==3 and value["fit_started_after_lock"]
def test_24_grouped_folds():
    value=load("training_lock_report.json"); assert value["fold_counts"]=={"0":5,"1":5,"2":5} and value["group_unit"]=="whole_session_id"
def test_25_candidate_selection():
    value=load("candidate_selection_report.json"); assert value["all_required_gates_passed"] and value["audit_labels_read_count"]==0
def test_26_calibration_isolation():
    value=load("calibration_report.json"); assert value["method"]=="sigmoid" and value["audit_row_count"]==0 and len(value["sessions_only"])==5
def test_27_conformal_isolation():
    value=load("conformal_report.json"); assert value["method"]=="mondrian_class_conditional" and value["audit_row_count"]==0 and value["coverage"]>=.95
def test_28_pre_audit_lock():
    value=load("pre_audit_lock_report.json"); assert value["audit_labels_read_count"]==0 and value["audit_inference_call_count"]==0 and value["committed_before_unlock"]
def test_29_single_audit_inference():
    value=load("audit_unlock_report.json"); assert value["audit_inference_call_count"]==1 and value["repeated_inference_count"]==0 and value["tuning_after_unlock_count"]==0
def test_30_window_gates(): assert all(load("internal_audit_metrics.json")["gates"].values())
def test_31_per_class_support():
    rows=load("internal_audit_per_class.json")["classes"]; assert {x["class"] for x in rows}=={"benign","auth_failures","beacon","low_rate_dos","port_scan","web_probe"} and all(x["recall"]>=.9 for x in rows)
def test_32_episode_gates():
    value=load("internal_audit_episode_metrics.json"); assert value["attack_episode_recall"]>=.95 and value["episode_precision"]>=.95 and value["detection_by_second"]>=.95 and value["benign_episode_false_alert_rate"]<=.05
def test_33_conformal_gates():
    value=load("calibration_conformal_audit.json"); assert value["overall_coverage"]>=.95 and value["empty_set_rate"]<=.05 and value["wrong_only_rate"]==0
def test_34_bootstrap_contract():
    value=load("internal_audit_bootstrap.json"); assert value["iterations"]==5000 and value["seed"]==42 and value["sampling_unit"]=="whole_session_id"
def test_35_runtime_gates(): assert load("runtime_regression_report.json")["all_gates_passed"]
def test_36_latency_gates(): assert load("latency_report.json")["passed"] and load("latency_report.json")["stage_count"]==11
def test_37_reconciliation():
    value=load("source_sink_reconciliation.json"); assert value["event_sets_equal"] and value["pending_event_count"]==0 and value["unaccounted_drop_count"]==0
def test_38_privacy():
    value=load("privacy_report.json"); assert value["passed"] and value["positive_finding_count"]==0 and all(value["negative_fixtures_detected"].values())
def test_39_instrumentation_equivalence(): assert load("instrumentation_equivalence_report.json")["semantic_equivalence_passed"]
def test_40_historical_integrity(): assert load("historical_integrity_report.json")["previous_stage_hashes_unchanged"] and load("historical_integrity_report.json")["historical_negative_result_preserved"]
def test_41_candidate_manifest():
    value=json.loads((ROOT/"ml/artifacts/v0_3_15_4/candidate_manifest.json").read_text(encoding="utf-8")); assert value["candidate_id"].startswith("v03154:") and not value["artifact_tracked"] and value["feature_contract_sha256"]
def test_42_policy_boundaries():
    value=load("v0_3_15_4_policy_result.json"); assert value["v03154_redevelopment_passed"] and value["candidate_ready_for_v0_3_15_5_prospective_evaluation"] and not any(value[key] for key in ["candidate_ready_for_v0_3_16_staging_connector_readiness","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration","production_ready","automatic_enforcement_ready","external_validation_completed","v0_3_16_allowed"])
