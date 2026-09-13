from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from tools.vnext.context import (
    NETWORK_CONTEXT_FEATURES, build_context_fact, build_context_profile,
    build_stable_entity, build_window_policy, context_fact_state,
    network_context_feature_values, ordering_status, resolve_entities,
)
from tools.vnext.contracts import ContractError, canonical_digest
from tools.vnext.correlation import (
    assert_correlation_leakage_free, build_attack_chain, build_incident_candidate,
    build_correlation_registry, correlate, map_attack_evidence,
)
from tools.vnext.detection import detect
from tools.vnext.features import build_feature_bundle
from tools.vnext.graph import EDGE_TYPES, GRAPH_FEATURES, attach_reasoning_nodes, build_interaction_graph, graph_feature_values, validate_interaction_graph
from tools.vnext.telemetry import verify_digest, with_digest
from tools.vnext.scenarios.registry import load_wave1_registry
from tools.vnext.scenarios.runtime import run_smoke


def _samples(scenario: str = "scenario_service_discovery"):
    definition = next(row for row in load_wave1_registry()["scenarios"] if row["scenario_id"] == scenario)
    return [run_smoke(definition) for _ in range(2)]


def _pipeline(scenario: str = "scenario_service_discovery"):
    samples = _samples(scenario)
    observations = [row["observation_bundle"] for row in samples]
    events = [row["events"] for row in samples]
    graph = build_interaction_graph(observations, events)
    features = [build_feature_bundle(obs, ev, historical_events=events[0] if index else [], interaction_graph=graph) for index, (obs, ev) in enumerate(zip(observations, events))]
    detections = [detect(row)[0] for row in features]
    return samples, observations, events, graph, features, detections


def _set_group(bundle, group_id: str, values: dict[str, float]):
    result = deepcopy(bundle)
    group = next(row for row in result["groups"] if row["group_id"] == group_id)
    group["status"] = "AVAILABLE"; group["values"].update(values)
    return result


def _context(entity_id: str, at: str, *fact_types: str):
    facts = [build_context_fact(entity_id, kind, True, source="engineering_asset_registry", provenance={"record_ref":f"asset/{index}"}, trust="DECLARED_HIGH_TRUST", first_seen=at, last_seen=at) for index, kind in enumerate(fact_types)]
    return build_context_profile(facts, at)


def _retime_observation(observation, event_time, ingest_time):
    base = {key: deepcopy(value) for key, value in observation.items() if key not in {"bundle_id", "canonical_digest"}}
    base["temporal_summary"] = {"event_time": event_time, "ingest_time": ingest_time}
    return with_digest(base, id_field="bundle_id", id_prefix="obs")


def test_entity_identity_is_deterministic_namespace_and_provenance_aware():
    args = ("ip", {"kind":"ip","address":"10.0.0.8","version":4})
    a = build_stable_entity(*args, namespace="lab-a", provenance_scope="dhcp-lease-1")
    assert a == build_stable_entity(*args, namespace="lab-a", provenance_scope="dhcp-lease-1")
    assert a["entity_id"] != build_stable_entity(*args, namespace="lab-b", provenance_scope="dhcp-lease-1")["entity_id"]
    assert a["entity_id"] != build_stable_entity(*args, namespace="lab-a", provenance_scope="dhcp-lease-2")["entity_id"]


def test_conservative_entity_resolution_states():
    a = build_stable_entity("host", {"kind":"host","hostname":"node-a"}, namespace="lab", provenance_scope="inventory")
    b = build_stable_entity("host", {"kind":"host","hostname":"node-a"}, namespace="lab", provenance_scope="sensor")
    assert resolve_entities(a, a, left_namespace="lab", right_namespace="lab", provenance_refs=["p"])["state"] == "EXACT"
    assert resolve_entities(a, b, left_namespace="lab", right_namespace="lab", provenance_refs=["p"], shared_identifiers=["node-a"])["state"] == "STRONG"
    assert resolve_entities(a, b, left_namespace="lab", right_namespace="lab", provenance_refs=["p"], shared_identifiers=["node-a"], temporal_overlap=False)["state"] == "WEAK"
    assert resolve_entities(a, b, left_namespace="lab", right_namespace="other", provenance_refs=["p"], shared_identifiers=["node-a"])["state"] == "UNRESOLVED"


def test_context_provenance_trust_and_staleness():
    now = datetime.now(timezone.utc); stamp = now.isoformat()
    entity = build_stable_entity("service", {"kind":"service","name":"monitor","port":8080}, namespace="lab", provenance_scope="compose")
    fact = build_context_fact(entity["entity_id"], "monitoring_system_role", True, source="asset_registry", provenance={"record_ref":"asset/1"}, trust="OBSERVED", first_seen=stamp, last_seen=stamp)
    profile = build_context_profile([fact], stamp)
    assert profile["facts"][0]["trust"] == "OBSERVED" and profile["facts"][0]["provenance"]
    assert context_fact_state(fact, (now+timedelta(seconds=5)).isoformat(), stale_after_seconds=10) == "ACTIVE"
    assert context_fact_state(fact, (now+timedelta(seconds=20)).isoformat(), stale_after_seconds=10) == "STALE"


def test_window_policy_and_lateness_are_explicit():
    policy = build_window_policy(10, 60, 600, 5)
    assert list(policy["horizons"]) == ["short", "behavior", "context"]
    assert ordering_status("2026-01-01T00:00:10Z", "2026-01-01T00:00:11Z", "2026-01-01T00:00:10Z", 5) == "ON_TIME"
    assert ordering_status("2026-01-01T00:00:08Z", "2026-01-01T00:00:11Z", "2026-01-01T00:00:10Z", 5) == "LATE_ACCEPTED"
    assert ordering_status("2026-01-01T00:00:01Z", "2026-01-01T00:00:11Z", "2026-01-01T00:00:10Z", 5) == "TOO_LATE"
    assert ordering_status(None, None, None, 5) == "UNKNOWN_ORDER"


def test_network_context_feature_count_and_fanout():
    sample = _samples()[0]
    values = network_context_feature_values(sample["events"])
    assert tuple(values) == NETWORK_CONTEXT_FEATURES and len(values) == 19
    assert values["port_fan_out"] >= 2 and values["failed_connection_ratio"] > 0


def test_graph_canonicalization_digest_and_typed_edges():
    _, observations, events, graph, *_ = _pipeline("scenario_web_path_enumeration")
    rebuilt = build_interaction_graph(observations, [list(reversed(row)) for row in events])
    assert rebuilt == graph
    assert {row["edge_type"] for row in graph["edges"]} <= EDGE_TYPES
    broken = deepcopy(graph); broken["edges"][0]["edge_type"] = "RELATED_TO"
    with pytest.raises(ContractError): validate_interaction_graph(broken)


def test_graph_ephemeral_entities_never_claim_canonical_identity():
    _, _, _, graph, *_ = _pipeline("scenario_web_path_enumeration")
    entities = [row for row in graph["nodes"] if row["node_type"] == "entity"]
    ephemeral = [row for row in entities if row["identity_scope"] == "ephemeral_graph_projection"]
    assert ephemeral and all(row["node_id"].startswith("eph_") and row["canonical_ref"] is None for row in ephemeral)
    assert all(row["canonical_ref"] is None for row in entities)
    broken = deepcopy(graph); broken["nodes"][next(index for index, row in enumerate(broken["nodes"]) if row["node_type"] == "entity")]["canonical_ref"] = "claimed-canonical-id"
    with pytest.raises(ContractError): validate_interaction_graph(broken)


def test_temporal_edges_accumulate_across_windows():
    _, _, _, graph, *_ = _pipeline("scenario_health_checks")
    assert any(row["edge_type"] == "PRECEDES" for row in graph["edges"])
    assert any(row["count"] > 1 and len(row["observation_ids"]) == 2 for row in graph["edges"])


def test_graph_features_are_interpretable_and_complete():
    _, _, _, graph, *_ = _pipeline("scenario_credential_brute_force")
    values = graph_feature_values(graph)
    assert tuple(values) == GRAPH_FEATURES and len(values) == 13
    assert values["weighted_degree"] > 0 and values["account_host_fan_out"] > 0


def test_correlation_is_deterministic_and_preserves_unknown():
    _, observations, _, graph, features, detections = _pipeline("scenario_health_checks")
    features = [_set_group(row, "network_context_v1", {"port_fan_out":1,"cross_window_recurrence":0,"endpoint_stability":0,"new_target_ratio":1,"historical_target_overlap":0}) for row in features]
    first = correlate(observations, features, detections, graph, None)
    second = correlate(observations, features, detections, graph, None)
    assert first == second and first["abstention"]["final_state"] == "UNKNOWN"


@pytest.mark.parametrize(("event_time", "ingest_time", "watermark", "expected"), [
    ("2026-01-01T00:00:10Z", "2026-01-01T00:00:11Z", "2026-01-01T00:00:10Z", "ON_TIME"),
    ("2026-01-01T00:00:08Z", "2026-01-01T00:00:11Z", "2026-01-01T00:00:10Z", "LATE_ACCEPTED"),
    ("2026-01-01T00:00:01Z", "2026-01-01T00:00:11Z", "2026-01-01T00:00:10Z", "TOO_LATE"),
    ("2026-01-01T00:00:08Z", None, "2026-01-01T00:00:10Z", "UNKNOWN_ORDER"),
])
def test_correlate_distinguishes_event_ingest_and_watermark(event_time, ingest_time, watermark, expected):
    _, observations, _, graph, features, detections = _pipeline("scenario_health_checks")
    observations = [_retime_observation(row, event_time, ingest_time) for row in observations]
    result = correlate(observations, features, detections, graph, None, allowed_lateness_seconds=5, watermark=watermark)
    assert result["ordering_statuses"] == [expected]


def test_local_unknown_can_be_improved_by_multi_window_evidence():
    _, observations, _, graph, features, detections = _pipeline()
    for detection in detections: assert detection["abstention"]["abstained"]
    features = [_set_group(row, "network_context_v1", {"port_fan_out":6,"cross_window_recurrence":1,"endpoint_stability":0.2,"new_target_ratio":0,"historical_target_overlap":1}) for row in features]
    result = correlate(observations, features, detections, graph, None)
    assert result["abstention"]["final_state"] == "CONTEXTUAL_HYPOTHESIS"
    assert result["hypotheses"][0]["hypothesis_id"] == "reconnaissance_progression"


def test_approved_scanner_stable_context_can_support_monitoring():
    _, observations, _, graph, features, detections = _pipeline()
    features = [_set_group(row, "network_context_v1", {"port_fan_out":6,"cross_window_recurrence":1,"endpoint_stability":0.2,"new_target_ratio":0,"historical_target_overlap":1}) for row in features]
    source = next(node["node_id"] for node in graph["nodes"] if node.get("entity_type") == "ip")
    context = _context(source, observations[-1]["window"]["end"], "approved_scanner_role", "expected_communication_relationship", "maintenance_window")
    result = correlate(observations, features, detections, graph, context)
    assert result["hypotheses"][0]["hypothesis_id"] == "benign_monitoring" and not result["abstention"]["abstained"]


def test_context_poisoning_does_not_make_changed_scanner_benign():
    _, observations, _, graph, features, detections = _pipeline()
    features = [_set_group(row, "network_context_v1", {"port_fan_out":10,"cross_window_recurrence":0,"endpoint_stability":0.1,"new_target_ratio":1,"historical_target_overlap":0}) for row in features]
    source = next(node["node_id"] for node in graph["nodes"] if node.get("entity_type") == "ip")
    result = correlate(observations, features, detections, graph, _context(source, observations[-1]["window"]["end"], "approved_scanner_role"))
    assert result["abstention"]["abstained"]
    assert any(row["kind"] == "context_poisoning_guard" for row in result["contradictory_evidence"])
    assert not (result["hypotheses"] and result["hypotheses"][0]["hypothesis_id"] == "benign_monitoring")


def test_health_context_changes_beacon_ambiguity_without_becoming_label():
    _, observations, _, graph, features, detections = _pipeline("scenario_health_checks")
    features = [_set_group(_set_group(_set_group(row,"network_context_v1",{"port_fan_out":1,"cross_window_recurrence":1,"endpoint_stability":1,"new_target_ratio":0,"historical_target_overlap":1}),"temporal_v1",{"periodicity_score":1}),"http_behavior_v1",{"repeated_path_ratio":0.75}) for row in features]
    source = next(node["node_id"] for node in graph["nodes"] if node.get("entity_type") == "ip")
    result = correlate(observations, features, detections, graph, _context(source, observations[-1]["window"]["end"], "monitoring_system_role", "expected_communication_relationship"))
    assert result["hypotheses"][0]["hypothesis_id"] == "benign_monitoring"


def test_incident_chain_and_multiple_attack_candidates_are_separate():
    _, observations, _, graph, features, detections = _pipeline()
    features = [_set_group(row, "network_context_v1", {"port_fan_out":6,"cross_window_recurrence":1,"endpoint_stability":0.2,"new_target_ratio":0,"historical_target_overlap":1}) for row in features]
    correlation = correlate(observations, features, detections, graph, None)
    mapping = map_attack_evidence(correlation); chain = build_attack_chain(correlation); incident = build_incident_candidate(correlation, mapping, chain)
    assert len(mapping["candidates"]) >= 2
    assert [row["stage_index"] for row in chain["stages"]] == list(range(len(chain["stages"])))
    assert incident["candidate_id"] != correlation["correlation_id"] and incident["status"] == "SUSPICIOUS"
    reasoning = attach_reasoning_nodes(graph, correlation, incident)
    assert {"correlation_result", "incident_candidate"} <= {row["node_type"] for row in reasoning["nodes"]}
    assert {"ASSOCIATED_WITH", "SUPPORTED_BY"} <= {row["edge_type"] for row in reasoning["edges"]}


def test_correlation_registry_is_machine_readable_and_implemented():
    registry = build_correlation_registry(); verify_digest(registry)
    assert len(registry["capabilities"]) == 5
    assert all(row["maturity"] == "implemented" and row["explanation_capability"] for row in registry["capabilities"])


@pytest.mark.parametrize("forbidden", ["scenario_id", "generator_family", "sealed_ground_truth", "expected_taxonomy_node", "realization_id"])
def test_correlation_leakage_rejected(forbidden: str):
    with pytest.raises(ContractError): assert_correlation_leakage_free({forbidden:"forbidden"})
