from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from collectors.shadow.diagnostic_evidence import LATENCY_STAGES, LatencyTrace, capture_synthetic_ack, instrumentation_equivalent, normalized_cpu_sample, privacy_findings
from tools.audit.validate_v03153_artifacts import validate as validate_artifacts
from tools.audit.validate_v03153_bundle import (
    CRLF_TRANSFORMATION,
    CorrectionError,
    validate as validate_bundle,
    validate_declared_correction,
)

ROOT=Path(__file__).resolve().parents[2]; REPORT=ROOT/"ml/reports/v0_3_15_3"


def load(name): return json.loads((REPORT/name).read_text(encoding="utf-8"))


def test_01_historical_hash_preservation():
    value=load("historical_integrity_report.json"); assert value["previous_stage_hashes_unchanged"] and value["v03152_bundle_integrity_verified"] and value["negative_result_preserved"]


def test_02_evidence_inventory():
    value=load("evidence_inventory.json"); assert value["artifact_count"]>=30 and value["missing_count"]>=3 and all(set(x)>={"artifact_id","exists","sha256","limitations"} for x in value["artifacts"])


def test_03_episode_trace_coverage():
    value=load("failure_episode_ledger.json"); assert value["episode_count"]==120 and len(value["episodes"])==120 and sum(x["label"]=="attack" for x in value["episodes"])==60 and all(x["window_ids"] for x in value["episodes"])


def test_04_root_cause_confidence_rules():
    protocol=yaml.safe_load((ROOT/"ml/protocols/v0_3_15_3_protocol.yaml").read_text(encoding="utf-8")); ledger=load("failure_episode_ledger.json"); assert set(protocol["confidence_rules"])=={"confirmed","probable","possible","unknown"}; assert all(x["supporting_evidence"] for x in ledger["episodes"] if x["root_cause_confidence"]=="confirmed")


def test_05_auth_failures_trace_completeness():
    value=load("auth_failures_episode_trace.json"); assert value["episode_count"]==12 and value["window_count"]==42 and len(value["raw_conn_windows"])==42


def test_06_scenario_label_consistency_schema():
    value=load("scenario_label_consistency_report.json"); assert value["class_count"]==5 and {x["class"] for x in value["classes"]}=={"auth_failures","beacon","low_rate_dos","port_scan","web_probe"} and not value["all_labels_consistent"]


def test_07_feature_semantics_audit():
    value=load("feature_semantics_audit.json"); assert value["feature_count"]==51 and len(value["features"])==51 and [x["position"] for x in value["features"]]==list(range(51))


def test_08_model_decision_funnel():
    value=load("model_decision_funnel.json"); assert value["overall"]["attack_labeled_windows"]==210 and value["subtype_false_negative_count"]==42 and value["conformal_abstention_count"]==126


def test_09_episode_state_decomposition():
    value=load("episode_state_decomposition.json"); assert value["hypothetical_diagnostic_episode_recall"]["current_full_policy"]==.4 and value["hypothetical_diagnostic_episode_recall"]["raw_frozen_class_decision"]==.8 and value["diagnostic_only"]


def test_10_diagnostic_inference_isolation():
    value=load("v0_3_15_3_policy_result.json"); assert value["diagnostic_inference_call_count"]==0 and value["historical_v03152_negative_result_preserved"]


def test_11_no_diagnostic_fit(): assert load("v0_3_15_3_policy_result.json")["diagnostic_fit_call_count"]==0


def test_12_no_diagnostic_threshold_search():
    value=load("v0_3_15_3_policy_result.json"); assert value["diagnostic_threshold_search_count"]==0 and value["diagnostic_feature_selection_count"]==0


def test_13_cpu_measurement_normalization():
    value=normalized_cpu_sample(system_percent=20,process_tree_percent=160,logical_cpu_count=8,sampling_interval_seconds=1); assert value["process_tree_cpu_percent_per_host"]==20 and load("cpu_measurement_semantics_report.json")["historical_measured_value"]["policy_passed"] is False


def test_14_exact_latency_instrumentation():
    trace=LatencyTrace("t","e"); [trace.mark(name,1000+i) for i,name in enumerate(LATENCY_STAGES)]; assert trace.analytical_record()["capture_to_sink_ns"]==10
    bad=LatencyTrace("t","e"); bad.mark(LATENCY_STAGES[0],10)
    with pytest.raises(ValueError): bad.mark(LATENCY_STAGES[1],9)


def test_15_raw_ack_evidence_capture(tmp_path):
    result=capture_synthetic_ack(wire=b'{"status":"accepted"}',status="accepted",event_id="e",runtime_directory=tmp_path,synthetic_sink=True); assert result["privacy_scan_passed"] and (tmp_path/result["raw_runtime_name"]).is_file() and not result["raw_ack_git_inclusion_permitted"]


def test_16_ack_privacy_scanning():
    fixtures={"token":"token=abcdefghi","password":"password=fixture","email":"a@example.org","ip":"192.0.2.1","url_query":"https://example.org/?x=y","cookie":"Cookie=abcdef","hostname":"host.internal","local_user_path":r"C:\Users\fixture\x"}; assert all(name in privacy_findings(value) for name,value in fixtures.items()); assert load("raw_ack_evidence_report.json")["positive_finding_count"]==0


def test_17_instrumentation_equivalence():
    base={"event_ids":["e"],"state_transitions":["review"]}; enhanced={**base,"latency_trace":{"x":1}}; assert instrumentation_equivalent(base,enhanced) and load("instrumentation_equivalence_report.json")["instrumentation_equivalence_passed"]


def test_18_next_cycle_decision_matrix():
    value=load("next_cycle_decision_matrix.json"); assert value["selected"]=="Track E — mixed redevelopment" and len(value["directions"])==7


def test_19_proposed_protocol_status():
    value=yaml.safe_load((ROOT/"ml/protocols/v0_3_15_4_protocol_candidate.yaml").read_text(encoding="utf-8")); assert value["status"]=="proposed_not_frozen" and value["readiness_policy"]["v0.3.16_allowed"] is False


def test_20_policy_readiness_consistency():
    value=load("v0_3_15_3_policy_result.json"); assert value["v03153_analysis_passed"] and all(value[key] is False for key in ["candidate_ready_for_v0_3_16_staging_connector_readiness","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration","production_ready","automatic_enforcement_ready","external_validation_completed"])


def test_21_bundle_validation():
    result=validate_bundle(REPORT/"v0_3_15_3_bundle_manifest.yaml",REPORT/"v0_3_15_3_bundle_manifest.sha256",ROOT); assert result["bundle_validator_passed"],result["errors"]


def test_22_documentation_consistency(): assert load("documentation_consistency_report.json")["semantic_documentation_validator_passed"]


def test_23_artifact_exclusion(): assert validate_artifacts(ROOT)["artifact_exclusion_validator_passed"]


def correction_entry(canonical: bytes, *, scope: str = "artifact") -> dict:
    import hashlib
    historical = canonical.replace(b"\n", b"\r\n")
    return {
        "package_version": "v0.3.15.3",
        "path": "fixture.txt",
        "scope": scope,
        "historical_sha256": hashlib.sha256(historical).hexdigest(),
        "canonical_git_blob_sha256": hashlib.sha256(canonical).hexdigest(),
        "historical_size": len(historical),
        "canonical_size": len(canonical),
        "transformation": CRLF_TRANSFORMATION,
        "status": "accepted",
    }


def test_24_explicit_historical_mapping():
    canonical = b"first\nsecond\n"
    entry = correction_entry(canonical)
    validate_declared_correction(entry, path="fixture.txt", scope="artifact", historical_sha256=entry["historical_sha256"], historical_size=entry["historical_size"], canonical=canonical)


def test_25_unknown_correction_rejected():
    canonical = b"first\nsecond\n"
    entry = correction_entry(canonical)
    with pytest.raises(CorrectionError, match="correction_missing"):
        validate_declared_correction(None, path="fixture.txt", scope="artifact", historical_sha256=entry["historical_sha256"], historical_size=entry["historical_size"], canonical=canonical)


def test_26_wrong_historical_digest_rejected():
    canonical = b"first\nsecond\n"
    entry = correction_entry(canonical)
    with pytest.raises(CorrectionError, match="historical_sha256"):
        validate_declared_correction(entry, path="fixture.txt", scope="artifact", historical_sha256="0" * 64, historical_size=entry["historical_size"], canonical=canonical)


def test_27_wrong_canonical_digest_rejected():
    canonical = b"first\nsecond\n"
    entry = correction_entry(canonical)
    entry["canonical_git_blob_sha256"] = "0" * 64
    with pytest.raises(CorrectionError, match="canonical_git_blob_sha256"):
        validate_declared_correction(entry, path="fixture.txt", scope="artifact", historical_sha256=entry["historical_sha256"], historical_size=entry["historical_size"], canonical=canonical)


def test_28_wrong_size_rejected():
    canonical = b"first\nsecond\n"
    entry = correction_entry(canonical)
    entry["canonical_size"] += 1
    with pytest.raises(CorrectionError, match="canonical_size"):
        validate_declared_correction(entry, path="fixture.txt", scope="artifact", historical_sha256=entry["historical_sha256"], historical_size=entry["historical_size"], canonical=canonical)


def test_29_arbitrary_newline_normalization_forbidden():
    import hashlib
    canonical = b"first\nsecond\n"
    historical = canonical.replace(b"\n", b"\r\n")
    with pytest.raises(CorrectionError, match="correction_missing"):
        validate_declared_correction(None, path="fixture.txt", scope="artifact", historical_sha256=hashlib.sha256(historical).hexdigest(), historical_size=len(historical), canonical=canonical)


def test_30_detached_manifest_uses_same_correction_contract():
    canonical = b"schema_version: fixture\n"
    entry = correction_entry(canonical, scope="detached_manifest")
    validate_declared_correction(entry, path="fixture.txt", scope="detached_manifest", historical_sha256=entry["historical_sha256"], historical_size=entry["historical_size"], canonical=canonical)
    with pytest.raises(CorrectionError, match="scope"):
        validate_declared_correction(entry, path="fixture.txt", scope="artifact", historical_sha256=entry["historical_sha256"], historical_size=entry["historical_size"], canonical=canonical)
