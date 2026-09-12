from __future__ import annotations

import json
from copy import deepcopy

import pytest

from tools.vnext.contracts import ContractError
from tools.vnext.scenarios.registry import load_wave1_registry, validate_wave1_registry
from tools.vnext.scenarios.runtime import (
    GENERATORS, DisposableTarget, ExecutionContext, SafetyLimits, TargetCapabilities,
    assert_generator_family_independence, build_realization, run_smoke,
)


@pytest.fixture(scope="module")
def registry():
    return validate_wave1_registry(load_wave1_registry())


def test_registry_is_unique_taxonomy_valid_and_not_scientifically_validated(registry):
    rows = registry["scenarios"]
    assert len(rows) == 24 == len({row["scenario_id"] for row in rows})
    assert sum(row["status"] == "implemented" for row in rows) == 22
    assert {row["scenario_id"] for row in rows if row["status"] == "planned"} == {"scenario_distributed_credential_guessing", "scenario_dns_callback"}
    assert all(row["status"] != "experimentally_validated" for row in rows)


@pytest.mark.parametrize("ids", [
    ["wave1_recon_family_a", "wave1_recon_family_b"],
    ["wave1_credential_family_a", "wave1_credential_family_b"],
    ["wave1_beacon_family_a", "wave1_beacon_family_b"],
])
def test_key_generator_families_have_independent_entrypoints_and_sources(ids):
    assert_generator_family_independence(ids)
    with pytest.raises(ContractError): assert_generator_family_independence([ids[0], ids[0]])


def test_realization_is_deterministic_and_dimension_change_changes_digest(registry):
    row = next(item for item in registry["scenarios"] if item["scenario_id"] == "scenario_service_discovery")
    with DisposableTarget() as target:
        left = build_realization(row, "wave1_recon_family_a", 19, target)
        right = build_realization(row, "wave1_recon_family_a", 19, target)
        changed = build_realization(row, "wave1_recon_family_a", 20, target)
    assert left == right and left["canonical_digest"] != changed["canonical_digest"]


def test_invalid_generator_target_capability_and_external_target_fail_closed(registry):
    row = next(item for item in registry["scenarios"] if item["scenario_id"] == "scenario_service_discovery")
    with DisposableTarget() as target:
        with pytest.raises(ContractError): build_realization(row, "wave1_beacon_family_a", 1, target)
        realization = build_realization(row, "wave1_recon_family_a", 1, target)
    invalid = TargetCapabilities("wave1-loopback", "127.0.0.1", 8080, (8080,), frozenset({"http_service"}))
    context = ExecutionContext("test", SafetyLimits(), 10**20)
    with pytest.raises(ContractError): GENERATORS["wave1_recon_family_a"].execute(row, realization, context, invalid)
    external = TargetCapabilities("outside", "8.8.8.8", 443, (443,), frozenset({"generic_tcp_services"}), False)
    with pytest.raises(ContractError): GENERATORS["wave1_recon_family_a"].execute(row, realization, context, external)


def test_dimension_and_malicious_benign_relation_validation(registry):
    broken = deepcopy(registry); broken["scenarios"][0]["intensity_model"]["dimension_ids"] = ["missing_dimension"]
    from tools.vnext.telemetry import with_digest
    broken["scenarios"][0] = with_digest({k: v for k, v in broken["scenarios"][0].items() if k != "canonical_digest"})
    broken = with_digest({k: v for k, v in broken.items() if k != "canonical_digest"})
    with pytest.raises(ContractError): validate_wave1_registry(broken)
    assert all(row["hard_benign_analogue_refs"] for row in registry["scenarios"] if row["taxonomy_node_id"].startswith("malicious."))


def test_every_implemented_scenario_executes_raw_parsed_normalized_bundle_without_leakage(registry):
    from tools.vnext.telemetry import assert_no_ground_truth_leakage
    forbidden_markers = {"filin", "scenario_"}
    for row in registry["scenarios"]:
        if row["status"] != "implemented": continue
        value = run_smoke(row, seed=11)
        observable = {"metadata": value["result"].observable_execution_metadata, "raw": value["result"].raw_records, "events": value["events"], "bundle": value["observation_bundle"]}
        text = json.dumps(observable, ensure_ascii=False).lower()
        assert not any(marker in text for marker in forbidden_markers)
        assert_no_ground_truth_leakage(observable)
        assert value["raw_evidence"]["evidence_id"] == "raw_" + value["raw_evidence"]["sha256"]
        assert value["observation_bundle"]["ground_truth_included"] is False
        assert set(row["telemetry_expectations"]["required"]) <= {event["event_type"] for event in value["events"]}
        assert value["temporary_outputs_removed_on_return"] is True
        assert value["sealed_ground_truth"]["scenario_id"] == row["scenario_id"]


def test_planned_scenarios_cannot_execute(registry):
    for row in registry["scenarios"]:
        if row["status"] == "planned":
            with pytest.raises(ContractError): run_smoke(row)


@pytest.mark.parametrize("malicious,benign,shared_type", [
    ("scenario_periodic_beacon", "scenario_health_checks", "http.request"),
    ("scenario_service_discovery", "scenario_approved_scanner", "network.flow"),
    ("scenario_credential_brute_force", "scenario_auth_misconfiguration", "auth.attempt"),
])
def test_counterfactuals_share_observables_but_labels_exist_only_in_sealed_layer(registry, malicious, benign, shared_type):
    rows = {row["scenario_id"]: row for row in registry["scenarios"]}
    left, right = run_smoke(rows[malicious], seed=5), run_smoke(rows[benign], seed=5)
    assert shared_type in {event["event_type"] for event in left["events"]} & {event["event_type"] for event in right["events"]}
    assert left["sealed_ground_truth"]["taxonomy_node_id"] != right["sealed_ground_truth"]["taxonomy_node_id"]
    for value in (left, right):
        assert "taxonomy_node_id" not in json.dumps(value["observation_bundle"])


def test_legacy_51_feature_contract_is_referenced_without_mutation(registry):
    from tools.vnext.telemetry import load_vnext_catalogs, validate_feature_compatibility
    provider = load_vnext_catalogs()["legacy_features"]
    validate_feature_compatibility(provider, {"network.flow", "dns.query", "http.request"})
    assert provider["feature_contract"]["feature_count"] == 51
    network_compatible = [row for row in registry["scenarios"] if "network.flow" in row["telemetry_expectations"]["expected_event_types"]]
    assert len(network_compatible) >= 14
