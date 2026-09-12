from __future__ import annotations

import json
from copy import deepcopy

import pytest

from tools.vnext.contracts import CONTRACT_ROOT, ContractError, canonical_digest, load_json
from tools.vnext.detection import detect, validate_detector_registry, validate_observability_matrix
from tools.vnext.features import (
    AUTH_FEATURES, DNS_FEATURES, HTTP_FEATURES, TEMPORAL_FEATURES, authentication_features,
    build_feature_bundle, dns_features, http_features, legacy_network_group,
    load_feature_provider_registry, temporal_features, validate_feature_bundle,
    validate_feature_provider_registry,
)
from tools.vnext.scenarios.registry import load_wave1_registry
from tools.vnext.scenarios.runtime import run_smoke
from tools.vnext.telemetry import validate_normalized_event, with_digest


@pytest.fixture(scope="module")
def rows():
    return {row["scenario_id"]: row for row in load_wave1_registry()["scenarios"]}


@pytest.fixture(scope="module")
def samples(rows):
    names = ["scenario_periodic_beacon", "scenario_jittered_beacon", "scenario_web_path_enumeration", "scenario_credential_brute_force", "scenario_password_spraying", "scenario_health_checks", "scenario_auth_misconfiguration", "scenario_sparse_port_scan"]
    return {name: run_smoke(rows[name], seed=31) for name in names}


def _bundle(sample):
    return build_feature_bundle(sample["observation_bundle"], sample["events"])


def _dns_event(template, index, timestamp, name, response="NOERROR"):
    base = {key: deepcopy(value) for key, value in template.items() if key not in {"event_id", "canonical_digest"}}
    base["event_type"] = "dns.query"; base["temporal"]["event_timestamp"] = timestamp; base["temporal"]["ordering"]["sequence"] = index
    base["action"] = {"name": "resolve", "outcome": "failure" if response == "NXDOMAIN" else "success", "status": response}
    base["payload"] = {"namespace": "dns.query", "question_name": name, "question_type": "A", "response_code": response, "answers": [] if response == "NXDOMAIN" else ["192.0.2.10"]}
    value = with_digest(base, id_field="event_id", id_prefix="evt"); return validate_normalized_event(value)


def test_provider_registries_and_observability_matrix_are_machine_valid():
    providers = validate_feature_provider_registry(load_feature_provider_registry())
    detectors = validate_detector_registry(load_json(CONTRACT_ROOT / "detector_capabilities_v1.json"))
    matrix = validate_observability_matrix(load_json(CONTRACT_ROOT / "behavior_observability_matrix_v1.json"))
    assert len(providers["providers"]) == 7 and len(detectors["detectors"]) == 2 and len(matrix["rows"]) == 8
    assert all(row["maturity"] != "experimentally_validated" for row in detectors["detectors"])


def test_feature_bundle_is_deterministic_canonical_and_digest_stable(samples):
    left = _bundle(samples["scenario_periodic_beacon"]); right = _bundle(samples["scenario_periodic_beacon"])
    assert left == right and validate_feature_bundle(left) == left
    assert [group["group_id"] for group in left["groups"]] == ["temporal_v1", "authentication_v1", "http_behavior_v1", "dns_v1", "legacy_network_v2", "network_context_v1", "interaction_graph_v1"]


def test_missing_telemetry_is_not_silently_zero(samples):
    bundle = _bundle(samples["scenario_periodic_beacon"]); groups = {group["group_id"]: group for group in bundle["groups"]}
    assert groups["dns_v1"]["status"] == "UNAVAILABLE_TELEMETRY" and groups["dns_v1"]["values"] == {}
    assert groups["legacy_network_v2"]["status"] == "UNSUPPORTED" and groups["legacy_network_v2"]["values"] == {}
    assert {row["status"] for row in bundle["missing_groups"]} >= {"UNAVAILABLE_TELEMETRY", "UNSUPPORTED"}


def test_temporal_features_have_exact_order_and_expected_regular_intervals(samples):
    sample = samples["scenario_periodic_beacon"]; events = [event for event in sample["events"] if event["event_type"] == "http.request"]
    for index,event in enumerate(events):
        event["temporal"]["event_timestamp"] = f"2026-01-01T00:00:0{index}Z"; events[index] = with_digest({k:v for k,v in event.items() if k!="canonical_digest"})
    group = temporal_features(sample["observation_bundle"], events)
    assert tuple(group["ordered_feature_names"]) == TEMPORAL_FEATURES
    assert group["values"]["mean_interval_ms"] == pytest.approx(1000) and group["values"]["interval_cv"] == pytest.approx(0)
    assert group["values"]["periodicity_score"] == pytest.approx(1)


def test_authentication_features_capture_concentration_and_account_fanout(samples):
    brute = authentication_features(samples["scenario_credential_brute_force"]["observation_bundle"], samples["scenario_credential_brute_force"]["events"])
    spray = authentication_features(samples["scenario_password_spraying"]["observation_bundle"], samples["scenario_password_spraying"]["events"])
    assert tuple(brute["ordered_feature_names"]) == AUTH_FEATURES and brute["values"]["failure_ratio"] == 1
    assert brute["values"]["max_account_concentration"] > spray["values"]["max_account_concentration"]
    assert spray["values"]["unique_accounts"] > brute["values"]["unique_accounts"]


def test_http_metadata_features_do_not_claim_payload_exploitation(samples):
    group = http_features(samples["scenario_web_path_enumeration"]["observation_bundle"], samples["scenario_web_path_enumeration"]["events"])
    assert tuple(group["ordered_feature_names"]) == HTTP_FEATURES and group["values"]["unique_paths"] == 6
    assert group["values"]["path_fanout"] == 1 and "user_agent_diversity" not in group["values"]
    assert group["missing_data"][0]["status"] == "UNSUPPORTED"


def test_dns_provider_works_from_existing_normalized_telemetry_contract(samples):
    sample = samples["scenario_periodic_beacon"]; template = sample["events"][0]
    events = [_dns_event(template,0,"2026-01-01T00:00:00Z","api.example.test"), _dns_event(template,1,"2026-01-01T00:00:01Z","x.api.example.test","NXDOMAIN"), _dns_event(template,2,"2026-01-01T00:00:02Z","api.example.test")]
    group = dns_features(sample["observation_bundle"], events)
    assert tuple(group["ordered_feature_names"]) == DNS_FEATURES and group["status"] == "AVAILABLE"
    assert group["values"]["query_count"] == 3 and group["values"]["unique_domains"] == 2
    assert group["values"]["nxdomain_ratio"] == pytest.approx(1/3)


def test_legacy_51_adapter_preserves_exact_values_order_and_contract_digest(samples):
    compatibility = load_json(CONTRACT_ROOT / "legacy_network_features_v2_compatibility.json")
    values = [index / 10 for index in range(51)]
    group = legacy_network_group(samples["scenario_periodic_beacon"]["observation_bundle"], samples["scenario_periodic_beacon"]["events"], values)
    assert group["ordered_feature_names"] == compatibility["feature_contract"]["ordered_feature_names"]
    assert list(group["values"].values()) == values
    assert compatibility["feature_contract"]["contract_sha256"] == "960726fce11ba55fcdbd6a93e4f588afc13fe4c3874b4b8c6f8322dcb94d8bf9"


@pytest.mark.parametrize("field", ["ground_truth", "scenario_id", "generator_id", "realization_id", "expected_taxonomy_node"])
def test_feature_and_prediction_path_reject_leakage(samples, field):
    bundle = _bundle(samples["scenario_periodic_beacon"]); broken = deepcopy(bundle); broken["groups"][0]["values"][field] = 1
    broken["groups"][0] = with_digest({k:v for k,v in broken["groups"][0].items() if k!="canonical_digest"}); broken = with_digest({k:v for k,v in broken.items() if k!="canonical_digest"})
    with pytest.raises(ContractError): detect(broken)


def test_detection_uses_no_ground_truth_ranks_hypotheses_and_links_evidence(samples):
    result, explanation = detect(_bundle(samples["scenario_credential_brute_force"]))
    assert result["ground_truth_used"] is False and explanation["ground_truth_used"] is False
    assert [row["rank"] for row in result["hypotheses"]] == list(range(1,len(result["hypotheses"])+1))
    assert [row["support_score"] for row in result["hypotheses"]] == sorted([row["support_score"] for row in result["hypotheses"]], reverse=True)
    evidence_ids = {row["evidence_id"] for row in explanation["evidence_items"]}
    assert set(result["evidence_refs"]) <= evidence_ids
    assert {row["evidence_type"] for row in explanation["evidence_items"]} == {"raw", "feature", "detector_rationale", "hypothesis"}
    assert all(explanation["layers"].values())
    assert any(row["direction"] == "contradicts" for row in explanation["evidence_items"])


def test_open_set_abstention_uses_multiple_signals_and_held_out_variants(samples):
    for name in ("scenario_jittered_beacon", "scenario_sparse_port_scan"):
        result,_ = detect(_bundle(samples[name]))
        assert result["known_behavior"] is False and result["abstention"]["abstained"] is True
        assert result["stages"]["specific_behavior"] is None
        assert result["abstention"]["reasons"]


def test_counterfactual_explanations_do_not_reduce_to_request_rate(samples):
    beacon_result,beacon_explanation = detect(_bundle(samples["scenario_periodic_beacon"]))
    health_result,health_explanation = detect(_bundle(samples["scenario_health_checks"]))
    assert {row["source_feature"] for row in beacon_explanation["evidence_items"]} >= {"temporal_v1.periodicity_score", "http_behavior_v1.error_ratio"}
    assert any(row["direction"] == "contradicts" for row in beacon_explanation["evidence_items"])
    assert beacon_result["known_behavior"] is False or health_result["known_behavior"] is False


def test_unknown_detector_and_invalid_legacy_vector_are_rejected(samples):
    with pytest.raises(ContractError): detect(_bundle(samples["scenario_periodic_beacon"]), {"detector_ids":["missing_detector"]})
    with pytest.raises(ContractError): legacy_network_group(samples["scenario_periodic_beacon"]["observation_bundle"], samples["scenario_periodic_beacon"]["events"], [0.0]*50)


def test_engineering_corpus_is_explicitly_non_scientific_and_held_out():
    corpus = load_json(CONTRACT_ROOT / "engineering_fixture_corpus_v1.json")
    assert corpus["scientific_evidence"] is False and corpus["held_out_cases"]
    assert not set(corpus["known_cases"]) & set(corpus["held_out_cases"])
    assert corpus["canonical_digest"] == canonical_digest(corpus, excluded_fields=("canonical_digest",))
