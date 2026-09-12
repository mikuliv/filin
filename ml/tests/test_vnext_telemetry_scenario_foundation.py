from __future__ import annotations

from copy import deepcopy

import pytest

from tools.vnext.contracts import CONTRACT_ROOT, ContractError, SCHEMA_NAMES, load_json, validate_schema_foundation
from tools.vnext.telemetry import (
    GROUND_TRUTH_KEYS,
    assert_no_ground_truth_leakage,
    audit_telemetry_scenario_foundation,
    build_scenario_realization,
    load_vnext_catalogs,
    validate_behavior_requirements,
    validate_dimension_registry,
    validate_feature_compatibility,
    validate_generator_registry,
    validate_normalized_event,
    validate_observation_bundle,
    validate_scenario_definition,
    validate_scenario_realization,
    validate_telemetry_catalog,
    with_digest,
)


HEX_A = "a" * 64
HEX_B = "b" * 64


def sample_event() -> dict:
    value = {
        "schema_version": "normalized_security_event_v1",
        "event_id": "evt_" + HEX_A,
        "event_type": "network.flow",
        "stage": "normalized",
        "source": {"source_type": "network_metadata", "source_product": "Zeek", "source_component": "conn", "collector": "zeek_collector", "collector_version": "v1"},
        "temporal": {"event_timestamp": "2026-01-01T00:00:00Z", "ingest_timestamp": "2026-01-01T00:00:01Z", "ordering": {"domain": "sensor-a", "sequence": 1}},
        "entity_refs": [],
        "action": {"name": "connect", "outcome": "success", "status": "observed"},
        "payload": {"namespace": "network.flow", "source": {"ip": "192.0.2.1", "port": 12345}, "destination": {"ip": "198.51.100.2", "port": 443}, "transport": "tcp", "bytes": 512, "packets": 8},
        "provenance": {
            "source_record_id": "conn:1",
            "raw_evidence": {"evidence_id": "raw_" + HEX_A, "artifact_type": "log", "sha256": HEX_A, "size_bytes": 1024, "locator": "captures/run-a/conn.log", "record_offset": 1},
            "transformation_chain": [
                {"stage": "parsed", "component": "zeek_parser", "version": "v1", "input_digest": HEX_A, "output_digest": HEX_B},
                {"stage": "normalized", "component": "vnext_normalizer", "version": "v1", "input_digest": HEX_B, "output_digest": HEX_A},
            ],
        },
        "enrichments": [],
    }
    return with_digest(value)


def sample_scenario(catalogs: dict) -> dict:
    generator_id = "legacy_network_family_a_adapter"
    value = {
        "schema_version": "scenario_definition_v2",
        "scenario_id": "scenario_periodic_callback_a",
        "purpose_ru": "Проверить контракт будущего периодического обратного вызова.",
        "status": "planned",
        "taxonomy_node_id": "malicious.command_and_control.beaconing",
        "scenario_variant": "steady_http_callback",
        "generator_requirements": {"allowed_generator_ids": [generator_id], "implementation_separation_required": True},
        "telemetry_expectations": {"required": ["network.flow", "http.request"], "useful": ["tls.handshake"], "expected_event_types": ["network.flow", "http.request"]},
        "environment_requirements": {"services": ["http_target"], "target_capabilities": ["http_callback"]},
        "parameter_constraints": {"interval_ms": [1000, 60000], "jitter_ratio": [0, 0.5]},
        "intensity_model": {"dimension_ids": ["interval_ms", "jitter_ratio", "payload_size"], "default_profile": {"interval_ms": 5000, "jitter_ratio": 0.1, "payload_size": 64}},
        "expected_observable_behavior": ["Повторяющиеся исходящие HTTP-соединения."],
        "forbidden_observable_fields": sorted(GROUND_TRUTH_KEYS),
        "forbidden_marker_patterns": ["filin", "scenario_", "generator_", "attack_label"],
        "counterfactual_refs": ["scenario_monitoring_http_callback"],
        "hard_benign_analogue_refs": ["benign.operations.monitoring", "benign.automation.api_polling"],
        "ground_truth_policy": {"storage_class": "external_sealed_ground_truth", "observable_access": "forbidden", "prediction_access": "forbidden"},
        "limitations": ["Периодичность не доказывает командное управление."],
    }
    return with_digest(value)


def test_all_vnext_schemas_parse_and_have_closed_versioned_roots() -> None:
    assert len(SCHEMA_NAMES) >= 19
    for name in SCHEMA_NAMES:
        validate_schema_foundation(load_json(CONTRACT_ROOT / name))


def test_normalized_event_is_typed_deterministic_and_provenance_aware() -> None:
    event = sample_event()
    assert validate_normalized_event(event) == event
    assert with_digest({key: value for key, value in event.items() if key != "canonical_digest"}) == event
    assert "raw" not in event and "content" not in event["provenance"]["raw_evidence"]


@pytest.mark.parametrize("mutation", ["missing_payload_field", "wrong_namespace", "missing_provenance", "inline_ground_truth"])
def test_invalid_event_payload_provenance_and_leakage_are_rejected(mutation: str) -> None:
    event = sample_event()
    if mutation == "missing_payload_field":
        del event["payload"]["packets"]
    elif mutation == "wrong_namespace":
        event["payload"]["namespace"] = "dns.query"
    elif mutation == "missing_provenance":
        del event["provenance"]
    else:
        event["payload"]["attack_label"] = "beacon"
    event = with_digest({key: value for key, value in event.items() if key != "canonical_digest"})
    with pytest.raises(ContractError):
        validate_normalized_event(event)


def test_observation_bundle_resolves_events_and_is_not_an_incident() -> None:
    event = sample_event()
    bundle = with_digest({
        "schema_version": "observation_bundle_v1", "bundle_id": "obs_" + HEX_A,
        "window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:01:00Z", "ordering_domain": "sensor-a"},
        "event_refs": [{"event_id": event["event_id"], "canonical_digest": event["canonical_digest"]}],
        "entity_refs": [], "aggregation": {"method": "fixed_window", "builder": "test", "builder_version": "v1", "causal": True, "event_count": 1},
        "telemetry_capability_refs": ["network.flow"], "raw_evidence_refs": [{"evidence_id": "raw_" + HEX_A, "sha256": HEX_A}],
        "feature_generation_refs": [], "correlation_context": {"correlation_keys": ["source.ip"], "parent_bundle_refs": []}, "ground_truth_included": False,
    })
    assert validate_observation_bundle(bundle, events=[event]) == bundle
    bad = deepcopy(bundle); bad["event_refs"][0]["event_id"] = "evt_" + HEX_B; bad = with_digest({key: value for key, value in bad.items() if key != "canonical_digest"})
    with pytest.raises(ContractError):
        validate_observation_bundle(bad, events=[event])
    assert "incident_id" not in bundle


def test_catalogs_require_valid_taxonomy_telemetry_and_maturity() -> None:
    catalogs = load_vnext_catalogs()
    validate_telemetry_catalog(catalogs["telemetry"])
    validate_behavior_requirements(catalogs["requirements"], catalogs["taxonomy"], catalogs["telemetry"])
    invalid_ref = deepcopy(catalogs["requirements"]); invalid_ref["requirements"][0]["taxonomy_node_id"] = "malicious.missing"
    invalid_ref = with_digest({key: value for key, value in invalid_ref.items() if key != "canonical_digest"})
    with pytest.raises(ContractError):
        validate_behavior_requirements(invalid_ref, catalogs["taxonomy"], catalogs["telemetry"])
    invalid_maturity = deepcopy(catalogs["telemetry"]); invalid_maturity["sources"][0]["capabilities"][0]["maturity"] = "experimentally_validated"
    invalid_maturity = with_digest({key: value for key, value in invalid_maturity.items() if key != "canonical_digest"})
    with pytest.raises(ContractError):
        validate_telemetry_catalog(invalid_maturity)


def test_hard_benign_analogues_cover_each_attack_family() -> None:
    catalogs = load_vnext_catalogs()
    rows = catalogs["requirements"]["requirements"]
    assert len(rows) == 8
    assert all(row["hard_benign_analogue_node_ids"] for row in rows)
    assert all(all(ref.startswith("benign.") for ref in row["hard_benign_analogue_node_ids"]) for row in rows)


def test_behavior_specific_dimensions_are_disjoint_and_reject_global_leakage() -> None:
    catalogs = load_vnext_catalogs()
    validate_dimension_registry(catalogs["dimensions"], catalogs["taxonomy"])
    broken = deepcopy(catalogs["dimensions"])
    dimension = broken["behavior_designs"][0]["required_dimensions"][0]
    broken["behavior_designs"][0]["optional_dimensions"].append(dimension)
    broken = with_digest({key: value for key, value in broken.items() if key != "canonical_digest"})
    with pytest.raises(ContractError):
        validate_dimension_registry(broken, catalogs["taxonomy"])


def test_generator_capability_and_scenario_compatibility() -> None:
    catalogs = load_vnext_catalogs()
    validate_generator_registry(catalogs["generators"], catalogs["taxonomy"], catalogs["dimensions"], catalogs["telemetry"])
    scenario = sample_scenario(catalogs)
    assert validate_scenario_definition(scenario, catalogs["taxonomy"], catalogs["generators"], catalogs["requirements"])
    mismatch = deepcopy(scenario); mismatch["taxonomy_node_id"] = "malicious.collection_exfiltration.dns_tunneling"
    mismatch = with_digest({key: value for key, value in mismatch.items() if key != "canonical_digest"})
    with pytest.raises(ContractError):
        validate_scenario_definition(mismatch, catalogs["taxonomy"], catalogs["generators"], catalogs["requirements"])


def test_scenario_realization_is_deterministic_and_separate_from_observation() -> None:
    catalogs = load_vnext_catalogs()
    scenario = sample_scenario(catalogs)
    args = (scenario, "legacy_network_family_a_adapter", 42, {"interval_ms": 5000, "jitter_ratio": 0.1, "payload_size": 64}, {"environment_id": "env-a", "services": ["http_target"], "target_id": "target-a"}, {"vault_id": "vault-a", "label_id": "label-a"})
    left = build_scenario_realization(*args)
    right = build_scenario_realization(*args)
    changed = build_scenario_realization(scenario, args[1], 43, args[3], args[4], args[5])
    assert left == right and left["realization_id"] != changed["realization_id"]
    assert "events" not in left and validate_scenario_realization(left) == left


def test_ground_truth_keys_are_rejected_from_observations_and_features() -> None:
    with pytest.raises(ContractError):
        assert_no_ground_truth_leakage({"features": {"safe": 1.0}, "ground_truth": {"label": "attack"}})
    with pytest.raises(ContractError):
        assert_no_ground_truth_leakage({"features": {"generator_id": 1.0}})


def test_legacy_51_feature_provider_preserves_exact_contract_and_requires_inputs() -> None:
    catalogs = load_vnext_catalogs()
    provider = catalogs["legacy_features"]
    assert validate_feature_compatibility(provider, {"network.flow", "dns.query", "http.request"})
    assert provider["feature_contract"]["feature_count"] == len(provider["feature_contract"]["ordered_feature_names"]) == 51
    with pytest.raises(ContractError):
        validate_feature_compatibility(provider, {"network.flow"})
    changed = deepcopy(provider); changed["feature_contract"]["ordered_feature_names"][0] = "changed"
    changed = with_digest({key: value for key, value in changed.items() if key != "canonical_digest"})
    with pytest.raises(ContractError):
        validate_feature_compatibility(changed, {"network.flow", "dns.query", "http.request"})


def test_foundation_audit_is_non_scientific() -> None:
    result = audit_telemetry_scenario_foundation()
    assert result == {
        "valid": True, "telemetry_source_count": 11, "telemetry_type_count": 14,
        "behavior_requirement_count": 8, "dimension_count": 19, "behavior_design_count": 6,
        "generator_count": 11, "legacy_feature_count": 51, "scientific_execution_performed": False,
    }
