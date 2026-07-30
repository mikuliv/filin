from __future__ import annotations

import ast
import copy
import hashlib
import json
import struct
from pathlib import Path

import pytest
import yaml

import lab.network_validation.cli as cli_module
from lab.network_validation import candidate_identity, common_client, feature_adapter, freeze
from lab.network_validation.capture import build_capture_manifest, pcap_summary, validate_capture_set
from lab.network_validation.causal_guard import feature_order, guard_feature_rows
from lab.network_validation.cli import main as cli_main
from lab.network_validation.contracts import (
    CAPTURE_SCHEMA,
    EXECUTION_SCHEMA,
    MARKER_SCHEMA,
    LABEL_SCHEMA,
    ContractError,
    digest,
    load_json,
    validate_campaign,
    validate_event,
    validate_model_input,
    validate_sealed_label_mapping,
    validate_scenario,
    write_canonical,
)
from lab.network_validation.generators.base import GeneratorFamily, NetworkAction
from lab.network_validation.generators.family_a import FamilyA
from lab.network_validation.generators.family_b import FamilyB
from lab.network_validation.parameter_verification import observations_from_zeek, verify_parameters
from lab.network_validation.planning import plan_campaign, proxy_risks, validate_counterfactuals, validate_infrastructure_profiles, validate_split

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "lab/network_validation"
CAMPAIGN = PACKAGE / "config/technical_campaign.json"


def campaign() -> dict:
    return load_json(CAMPAIGN)


def scenario(token: str = "navigation_family_a") -> dict:
    return next(row for row in campaign()["scenarios"] if row["scenario_token"] == token)


def execution_event(token: str = "navigation_family_a") -> dict:
    row = scenario(token)
    return {
        "schema_version": EXECUTION_SCHEMA,
        "campaign_token": row["campaign_token"], "scenario_token": row["scenario_token"],
        "generator_family": row["generator_family"], "infrastructure_profile": row["infrastructure_profile"],
        "client_identity": common_client.CLIENT_IDENTITY, "target_identity": "target_a",
        "start_timestamp": "2026-01-01T00:00:00Z", "end_timestamp": "2026-01-01T00:00:01Z",
        "exit_code": 0, "execution_status": "technical_fixture_completed",
        "requested_parameter_digest": digest(row["parameter_vector"]), "client_image_digest": "sha256:" + "a" * 64,
        "target_image_digest": "sha256:" + "b" * 64, "network_identity": "validation_a",
    }


def marker_event() -> dict:
    return {
        "schema_version": MARKER_SCHEMA, "marker_nonce": "abcdef0123456789abcdef01",
        "campaign_token": "technical_fixture_campaign", "scenario_token": "navigation_family_a",
        "marker_type": "start", "monotonic_timestamp": 1.0,
        "wall_clock_timestamp": "2026-01-01T00:00:00Z", "source": common_client.CLIENT_IDENTITY,
        "capture_association": "capture_a",
    }


def target_map() -> dict[str, str]:
    return {
        "web": "http://target-a:8080", "api": "http://target-a:8080",
        "control": "http://target-a:8080", "multi_port": "target-a:8080",
        "implementation": "target_a", "network_identity": "validation_a",
    }


def capture_metadata(execution: dict, path: str = "captures/sample.pcap") -> dict:
    return {
        "capture_id": "capture_a", "campaign_token": execution["campaign_token"],
        "scenario_token": execution["scenario_token"], "session_token": "session_a",
        "generator_family": execution["generator_family"],
        "infrastructure_profile": execution["infrastructure_profile"],
        "sensor_identity": "sensor-capture", "docker_network_identity": execution["network_identity"],
        "capture_start": 1.0, "capture_end": 2.0, "source_container": "common-client",
        "target_container": execution["target_identity"], "pcap_path": path,
        "zeek_status": "completed", "execution_status": execution["execution_status"],
        "marker_association": "abcdef0123456789abcdef01",
        "parameter_verification_status": "passed",
    }


def environment_fixture(*, dirty: bool = False, resolved_images: bool = True) -> dict:
    value = {
        "schema_version": "network_validation_environment_lock_v1", "os": "Windows",
        "architecture": "AMD64", "python_version": "3.13.5",
        "pip_dependency_lock_digest": "a" * 64, "scikit_learn_version": "1.8.0",
        "joblib_version": "1.5.3", "docker_version": "28.3.3",
        "docker_compose_version": "2.39.2", "zeek_image_name": "zeek/zeek:7.0.5",
        "zeek_image_digest": "sha256:" + "b" * 64 if resolved_images else "unresolved",
        "client_image_digest": "sha256:" + "c" * 64 if resolved_images else "unresolved",
        "target_image_digests": {"target_a": "sha256:" + "d" * 64, "target_b": "sha256:" + "e" * 64} if resolved_images else {},
        "source_git_commit": "f" * 40, "dirty_working_tree": dirty,
        "feature_contract_digest": hashlib.sha256((ROOT / "ml/experiments/v0_3_15_4/feature_contract_v2.yaml").read_bytes()).hexdigest(),
        "feature_order_digest": digest(feature_order()), "timezone": "UTC", "locale": "ru_RU",
    }
    value["canonical_digest"] = digest(value)
    return value


def write_pcap(path: Path) -> None:
    packet = b"\x00" * 60
    path.write_bytes(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1) + struct.pack("<IIII", 1, 0, len(packet), len(packet)) + packet)


def test_campaign_and_all_twelve_scenarios_are_strictly_valid():
    value = validate_campaign(campaign())
    assert len(value["scenarios"]) == 12
    assert {(row["behavior_type"], row["generator_family"]) for row in value["scenarios"]} == {(behavior, family) for behavior in FamilyA.supported_behaviors for family in {"family_a", "family_b"}}


def test_scenario_rejects_unknown_fields_and_labels():
    value = scenario(); value["label"] = "benign"
    with pytest.raises(ContractError, match="unknown fields"):
        validate_scenario(value)


def test_label_mapping_is_separate_and_strict():
    mapping = {"schema_version": LABEL_SCHEMA, "scenario_token": "scenario_a", "evaluation_label": "benign"}
    validate_sealed_label_mapping(mapping)
    with pytest.raises(ContractError):
        validate_sealed_label_mapping({**mapping, "generator_family": "family_a"})


@pytest.mark.parametrize("field", [
    "label", "class", "class_name", "scenario_id", "scenario_token", "campaign_id",
    "campaign_token", "generator_family", "infrastructure_profile", "target_implementation",
    "filename", "file_path", "directory", "pair_id", "marker_nonce",
])
def test_model_input_rejects_every_forbidden_metadata_field(field: str):
    order = feature_order(); row = {name: 0.0 for name in order}; row[field] = "forbidden"
    with pytest.raises(ContractError):
        validate_model_input(row, order)


@pytest.mark.parametrize(("field", "value"), [("requested_request_count", 0), ("requested_spacing_ms", -1), ("requested_payload_size", 1048577), ("seed", -1)])
def test_scenario_rejects_parameter_ranges(field: str, value: int):
    item = scenario(); item[field] = value
    with pytest.raises(ContractError):
        validate_scenario(item)


def test_generator_family_interface_and_supported_semantics():
    assert issubclass(FamilyA, GeneratorFamily) and issubclass(FamilyB, GeneratorFamily)
    for row in campaign()["scenarios"]:
        family = FamilyA() if row["generator_family"] == "family_a" else FamilyB()
        actions = family.actions(row)
        assert actions and all(isinstance(action, NetworkAction) for action in actions)


def test_generator_implementations_do_not_import_each_other():
    for filename, forbidden in (("family_a.py", "family_b"), ("family_b.py", "family_a")):
        tree = ast.parse((PACKAGE / "generators" / filename).read_text(encoding="utf-8"))
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert all(forbidden not in name for name in imports)


def test_generator_families_are_behaviorally_independent():
    a, b = scenario("navigation_family_a"), scenario("navigation_family_b")
    assert FamilyA().actions(a) != FamilyB().actions(b)
    assert ast.dump(ast.parse((PACKAGE / "generators/family_a.py").read_text(encoding="utf-8"))) != ast.dump(ast.parse((PACKAGE / "generators/family_b.py").read_text(encoding="utf-8")))


def test_generator_families_have_matching_semantic_action_shapes_and_are_deterministic():
    for behavior in FamilyA.supported_behaviors:
        left = scenario(f"{behavior}_family_a" if behavior != "credential_rejection" else "credential_rejection_family_a")
        right = scenario(f"{behavior}_family_b" if behavior != "credential_rejection" else "credential_rejection_family_b")
        left_actions, right_actions = FamilyA().actions(left), FamilyB().actions(right)
        assert len(left_actions) == len(right_actions)
        assert {action.kind for action in left_actions} == {action.kind for action in right_actions}
        assert {action.capability for action in left_actions} == {action.capability for action in right_actions}
        assert left_actions == FamilyA().actions(left)
        assert right_actions == FamilyB().actions(right)


def test_generators_reject_unknown_behavior():
    item = scenario(); item["behavior_type"] = "unknown"
    with pytest.raises(ValueError, match="unsupported"):
        FamilyA().actions(item)


def test_parameter_vectors_change_actions():
    original = scenario("service_discovery_family_a")
    changed = copy.deepcopy(original); changed["parameter_vector"]["ports"] = [9001, 9002, 9003, 9004]
    assert FamilyA().actions(original) != FamilyA().actions(changed)


def test_every_configured_parameter_vector_changes_its_action_plan():
    alternatives = {
        "navigation_family_a": {"path_rotation": 2}, "navigation_family_b": {"phase_rotation": 1},
        "credential_rejection_family_a": {"credential_rotation": 3}, "credential_rejection_family_b": {"session_rotation": 3},
        "periodic_callback_family_a": {"cadence_mode": "jittered"}, "periodic_callback_family_b": {"cadence_mode": "steady"},
        "throttled_pressure_family_a": {"burst_width": 2}, "throttled_pressure_family_b": {"phase_width": 3},
        "service_discovery_family_a": {"ports": [9001, 9002, 9003, 9004]}, "service_discovery_family_b": {"port_start": 89, "port_width": 5},
        "path_inspection_family_a": {"path_set": "other"}, "path_inspection_family_b": {"path_set": "other"},
    }
    for token, parameter_vector in alternatives.items():
        original = scenario(token); changed = copy.deepcopy(original); changed["parameter_vector"] = parameter_vector
        family = FamilyA() if original["generator_family"] == "family_a" else FamilyB()
        assert family.actions(original) != family.actions(changed), token


def test_common_client_has_one_identity_and_common_headers():
    assert common_client.CLIENT_IDENTITY == "network-validation-common-client"
    assert common_client.COMMON_HEADERS["X-Client-Role"] == "traffic-client"
    for row in campaign()["scenarios"]:
        assert not ({"client_identity", "source_role", "user_agent", "client_image"} & row.keys())


def test_common_client_uses_one_neutral_background_dns_name(monkeypatch: pytest.MonkeyPatch):
    resolved = []
    monkeypatch.setattr(common_client, "_request", lambda *args, **kwargs: {"kind": "http", "status": 200})
    monkeypatch.setattr(common_client.socket, "getaddrinfo", lambda host, port: resolved.append(host) or [])
    common_client._background(scenario(), target_map())
    assert resolved == ["background.invalid"]


def test_common_client_rejects_class_specific_or_incomplete_target_map():
    with pytest.raises(ValueError, match="fields"):
        common_client.validate_target_map({"web": "http://target-a:8080", "label": "benign"})


def test_common_client_runtime_writes_contract_events(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    row = scenario()
    monkeypatch.setattr(common_client, "execute_action", lambda *args, **kwargs: {"kind": "http", "status": 200})
    monkeypatch.setattr(common_client, "_background", lambda *args, **kwargs: [])
    monkeypatch.setattr(common_client.time, "sleep", lambda _: None)
    monkeypatch.setattr(common_client, "_marker", lambda kind, *_: {**marker_event(), "marker_type": kind})
    result = common_client.run_scenario(row, target_map(), tmp_path, "capture_a")
    validate_event(result, "execution")
    assert load_json(tmp_path / "client_observations.json")["technical_fixture"] is True


def test_infrastructure_profiles_are_materially_distinct():
    profiles = campaign()["infrastructure_profiles"]
    validate_infrastructure_profiles(profiles)
    assert profiles[0]["subnet"] != profiles[1]["subnet"]
    assert profiles[0]["target_implementation"] != profiles[1]["target_implementation"]


def test_campaign_planner_allows_the_same_behavior_in_both_profiles():
    value = campaign(); extra = copy.deepcopy(scenario("navigation_family_a"))
    extra["scenario_token"] = "navigation_profile_b"; extra["infrastructure_profile"] = "profile_b"
    value["scenarios"].append(extra)
    assert plan_campaign(value)["scenario_count"] == 13


def test_counterfactual_pairs_reference_distinct_valid_scenarios():
    value = campaign(); validate_counterfactuals(value)
    assert len(value["counterfactual_pairs"]) == 6
    assert len(value["counterfactual_requirements"]) == 9


def test_counterfactual_pair_rejects_missing_reference():
    value = campaign(); value["counterfactual_pairs"][0]["right"] = "missing"
    with pytest.raises(ContractError):
        validate_counterfactuals(value)


def test_counterfactual_pair_rejects_changed_invariant():
    value = campaign()
    right = next(row for row in value["scenarios"] if row["scenario_token"] == value["counterfactual_pairs"][0]["right"])
    right["requested_spacing_ms"] += 1
    with pytest.raises(ContractError, match="invariant"):
        validate_counterfactuals(value)


def test_background_policy_is_label_independent_and_nonzero():
    policies = [row["background_traffic_policy"] for row in campaign()["scenarios"]]
    assert all(sum(policy.values()) > 0 for policy in policies)
    assert all("label" not in policy for policy in policies)


def test_execution_and_marker_event_contracts_reject_unknown_fields():
    validate_event(execution_event(), "execution"); validate_event(marker_event(), "marker")
    bad = marker_event(); bad["label"] = "benign"
    with pytest.raises(ContractError):
        validate_event(bad, "marker")


def test_capture_manifest_checks_pcap_sha_and_execution_link(tmp_path: Path):
    pcap = tmp_path / "captures/sample.pcap"; pcap.parent.mkdir(); write_pcap(pcap)
    execution = execution_event()
    metadata = capture_metadata(execution)
    manifest = build_capture_manifest(metadata, tmp_path, execution)
    assert manifest["schema_version"] == CAPTURE_SCHEMA and manifest["packet_count"] == 1
    validate_capture_set([manifest], tmp_path, {execution["scenario_token"]: execution})
    pcap.write_bytes(pcap.read_bytes() + b"x")
    with pytest.raises(ContractError, match="SHA"):
        validate_capture_set([manifest], tmp_path, {execution["scenario_token"]: execution})


def test_capture_set_rejects_duplicate_capture_ids(tmp_path: Path):
    with pytest.raises(ValueError, match="duplicate"):
        validate_capture_set([{"capture_id": "same"}, {"capture_id": "same"}], tmp_path, {})


def test_capture_manifest_rejects_missing_absolute_empty_and_invalid_interval(tmp_path: Path):
    execution = execution_event()
    with pytest.raises(ContractError, match="missing"):
        build_capture_manifest(capture_metadata(execution, "captures/missing.pcap"), tmp_path, execution)
    pcap = tmp_path / "captures/sample.pcap"; pcap.parent.mkdir(); write_pcap(pcap)
    with pytest.raises(ContractError, match="relative"):
        build_capture_manifest(capture_metadata(execution, str(pcap.resolve())), tmp_path, execution)
    invalid_interval = capture_metadata(execution); invalid_interval["capture_end"] = invalid_interval["capture_start"]
    with pytest.raises(ContractError, match="interval"):
        build_capture_manifest(invalid_interval, tmp_path, execution)
    empty = tmp_path / "captures/empty.pcap"; empty.write_bytes(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    with pytest.raises(ContractError, match="empty"):
        build_capture_manifest(capture_metadata(execution, "captures/empty.pcap"), tmp_path, execution)


def test_capture_set_rejects_missing_execution_and_marker_mismatch(tmp_path: Path):
    pcap = tmp_path / "captures/sample.pcap"; pcap.parent.mkdir(); write_pcap(pcap)
    execution = execution_event(); manifest = build_capture_manifest(capture_metadata(execution), tmp_path, execution)
    with pytest.raises(ContractError, match="execution reference"):
        validate_capture_set([manifest], tmp_path, {})
    start = marker_event(); end = {**start, "marker_type": "end"}
    with pytest.raises(ContractError, match="linkage"):
        validate_capture_set([manifest], tmp_path, {execution["scenario_token"]: execution}, {execution["scenario_token"]: [{**start, "capture_association": "wrong"}, end]})


def test_capture_manifest_has_canonical_serialization(tmp_path: Path):
    pcap = tmp_path / "captures/sample.pcap"; pcap.parent.mkdir(); write_pcap(pcap)
    execution = execution_event(); manifest = build_capture_manifest(capture_metadata(execution), tmp_path, execution)
    output = tmp_path / "manifest.json"; write_canonical(output, manifest)
    assert output.read_bytes() == json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"


def test_parameter_observations_come_from_zeek_and_support_not_observable(tmp_path: Path):
    (tmp_path / "conn.log").write_text('{"ts":1.0,"duration":0.5,"conn_state":"SF"}\n', encoding="utf-8")
    (tmp_path / "http.log").write_text('{"ts":1.1,"method":"GET","host":"x","uri":"/","request_body_len":0}\n', encoding="utf-8")
    observed = observations_from_zeek(tmp_path)
    assert observed["request_count"] == 1 and observed["evidence_sources"]["request_count"] == "zeek:http.log"
    report = verify_parameters(scenario(), observed)
    assert {row["status"] for row in report["checks"]} <= {"passed", "failed", "not_observable"}
    assert any(row["status"] == "not_observable" for row in verify_parameters(scenario(), {"evidence_source": "zeek:conn.log"})["checks"])


def test_empty_zeek_logs_do_not_become_zero_observations(tmp_path: Path):
    for name in ("conn.log", "http.log", "dns.log"):
        (tmp_path / name).write_text("", encoding="utf-8")
    observed = observations_from_zeek(tmp_path)
    assert all(observed[name] is None for name in (
        "request_count", "episode_duration_seconds", "inter_request_spacing_ms",
        "payload_size", "retry_count", "timeout_behavior", "response_order",
        "background_traffic_level",
    ))
    report = verify_parameters(scenario(), observed)
    assert report["status"] == "incomplete"
    assert all(row["status"] == "not_observable" and row["evidence_source"] == "not_available" for row in report["checks"])


def test_parameter_verification_rejects_bad_tolerance_and_preserves_failures():
    with pytest.raises(ContractError, match="tolerance"):
        verify_parameters(scenario(), {}, {"request_count": -1})
    with pytest.raises(ContractError, match="tolerance"):
        verify_parameters(scenario(), {}, {"inter_request_spacing_ms": {"value": 1, "unit": "seconds"}})
    observed = {"request_count": 999, "evidence_sources": {"request_count": "zeek:http.log"}}
    report = verify_parameters(scenario(), observed, {"request_count": 0})
    assert report["status"] == "failed"
    assert next(row for row in report["checks"] if row["parameter"] == "request_count")["status"] == "failed"


def test_client_claim_without_network_evidence_is_not_observable():
    report = verify_parameters(scenario(), {"client_success": True})
    assert report["status"] == "incomplete"
    assert all(row["status"] == "not_observable" for row in report["checks"])


def test_causal_guard_accepts_exact_51_features_and_rejects_metadata():
    order = feature_order(); features = {name: 0.0 for name in order}
    guard_feature_rows([{"session_token": "s1", "causal_order": 0, "features": features}, {"session_token": "s1", "causal_order": 1, "features": features}])
    with pytest.raises(ContractError, match="metadata"):
        guard_feature_rows([{"session_token": "s1", "causal_order": 0, "features": features, "label": "benign"}])


def test_causal_guard_rejects_future_or_repeated_order_and_session_reentry():
    features = {name: 0.0 for name in feature_order()}
    with pytest.raises(ContractError, match="causal order"):
        guard_feature_rows([{"session_token": "s1", "causal_order": 1, "features": features}, {"session_token": "s1", "causal_order": 1, "features": features}])
    with pytest.raises(ContractError, match="contiguous"):
        guard_feature_rows([{"session_token": "s1", "causal_order": 0, "features": features}, {"session_token": "s2", "causal_order": 0, "features": features}, {"session_token": "s1", "causal_order": 1, "features": features}])


@pytest.mark.parametrize("causal_order", [-1, True, "1"])
def test_causal_guard_requires_integer_nonnegative_order(causal_order):
    with pytest.raises(ContractError, match="causal order"):
        guard_feature_rows([{"session_token": "s1", "causal_order": causal_order, "features": {name: 0.0 for name in feature_order()}}])


def test_feature_adapter_uses_exact_contract_and_isolates_session_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    observed_states = []

    def fake_extract(zeek_dir: Path, state, run_id: str):
        observed_states.append((state, run_id))
        return {name: 0.0 for name in feature_order()}, {"contains_label": False}

    monkeypatch.setattr(feature_adapter, "extract", fake_extract)
    adapter = feature_adapter.SessionFeatureAdapter(history_depth=3)
    first, provenance = adapter.extract_window(tmp_path, "session-a", 0)
    adapter.extract_window(tmp_path, "session-a", 1)
    adapter.extract_window(tmp_path, "session-b", 0)
    assert list(first["features"]) == feature_order()
    assert provenance["contains_label"] is False
    assert observed_states[0][0] is observed_states[1][0]
    assert observed_states[0][0] is not observed_states[2][0]
    with pytest.raises(ContractError, match="causal order"):
        adapter.extract_window(tmp_path, "session-a", 1)


def test_split_planner_enforces_family_infrastructure_target_and_session_boundaries():
    policy = campaign()["split_policy"]
    validate_split(policy["fixture_assignments"], policy)
    bad = copy.deepcopy(policy["fixture_assignments"]); bad[1]["generator_family"] = "family_a"
    with pytest.raises(ContractError, match="generator_family"):
        validate_split(bad, policy)


def test_split_planner_rejects_session_overlap():
    policy = campaign()["split_policy"]
    bad = copy.deepcopy(policy["fixture_assignments"]); bad[1]["session_token"] = bad[0]["session_token"]
    with pytest.raises(ContractError, match="session_token"):
        validate_split(bad, policy)


def test_split_planner_is_deterministic_and_rejects_impossible_policy():
    policy = campaign()["split_policy"]
    assert validate_split(copy.deepcopy(policy["fixture_assignments"]), copy.deepcopy(policy)) is None
    assert validate_split(copy.deepcopy(policy["fixture_assignments"]), copy.deepcopy(policy)) is None
    with pytest.raises(ContractError, match="development"):
        validate_split([copy.deepcopy(policy["fixture_assignments"][1])], policy)
    duplicate = copy.deepcopy(policy["fixture_assignments"]); duplicate.append(copy.deepcopy(duplicate[0]))
    with pytest.raises(ContractError, match="session_token"):
        validate_split(duplicate, policy)


def test_proxy_risk_validator_reports_obvious_class_fingerprints():
    risks = proxy_risks(campaign())
    assert {"class_to_port_lock", "class_to_target_lock", "class_to_infrastructure_lock", "non_overlapping_intensity"} <= {row["risk"] for row in risks}
    empty_background = campaign()
    for row in empty_background["scenarios"]:
        row["background_traffic_policy"] = {"http_requests": 0, "dns_queries": 0, "keepalive_count": 0}
    assert any(row["risk"] == "missing_background" for row in proxy_risks(empty_background))
    assert not any(row["risk"] == "unused_parameter_vector" for row in risks)


def test_proxy_validator_detects_family_metadata_counterfactual_and_unused_parameters():
    value = campaign()
    value["scenarios"] = [row for row in value["scenarios"] if row["generator_family"] == "family_a"]
    value["scenarios"][0]["user_agent"] = "class-specific"
    value["scenarios"][1]["technical_headers"] = {"X-Class": "one"}
    value["scenarios"][2]["parameter_vector"] = {"unused": "value"}
    risks = {row["risk"] for row in proxy_risks(value)}
    assert {"class_to_family_lock", "unique_user_agent", "unique_technical_header", "missing_counterfactual", "unused_parameter_vector"} <= risks


def test_plan_is_dry_and_does_not_create_artifacts(tmp_path: Path):
    before = list(tmp_path.iterdir()); result = plan_campaign(campaign())
    assert result["experiment_started"] is False and result["technical_fixture"] is True
    assert list(tmp_path.iterdir()) == before


def test_freeze_preview_rejects_unresolved_acceptance_criteria():
    env = environment_fixture(dirty=True, resolved_images=False)
    preview = freeze.freeze_preview(campaign(), env, "c" * 64, "d" * 40)
    assert preview["sealable"] is False and preview["unresolved_acceptance_fields"] and preview["unresolved_integrity_fields"]
    assert "proxy_risks" in preview["unresolved_integrity_fields"]
    with pytest.raises(ContractError):
        freeze.require_sealable(preview)


def test_freeze_preview_rejects_missing_environment_and_feature_order_mismatch():
    with pytest.raises(ContractError, match="environment lock"):
        freeze.freeze_preview(campaign(), {}, "c" * 64, "d" * 40)
    env = environment_fixture(); env["feature_order_digest"] = "0" * 64
    env["canonical_digest"] = digest({key: value for key, value in env.items() if key != "canonical_digest"})
    with pytest.raises(ContractError, match="feature order"):
        freeze.freeze_preview(campaign(), env, "c" * 64, "d" * 40)


def test_freeze_preview_rejects_inconsistent_candidate_identity():
    value = campaign(); value["candidate_identity"]["candidate_id"] = "wrong"
    with pytest.raises(ContractError, match="candidate"):
        freeze.freeze_preview(value, environment_fixture(), "c" * 64, "d" * 40)


def test_sealed_freeze_bytes_detect_modification():
    payload = b'{"schema_version":"fixture"}'
    freeze.verify_sealed_bytes(payload, hashlib.sha256(payload).hexdigest())
    with pytest.raises(ContractError, match="integrity"):
        freeze.verify_sealed_bytes(payload + b" ", hashlib.sha256(payload).hexdigest())


def test_environment_lock_has_no_absolute_paths_or_secrets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(freeze, "_command", lambda args: "083cc18" if "rev-parse" in args else "")
    value = freeze.environment_lock(ROOT, {})
    encoded = json.dumps(value)
    assert value["schema_version"] == "network_validation_environment_lock_v1"
    assert str(Path.home()) not in encoded and "password" not in encoded.lower()


def test_candidate_identity_uses_final_artifact_sha(tmp_path: Path):
    artifact = tmp_path / "candidate.bin"; artifact.write_bytes(b"final serialized bytes")
    sha = hashlib.sha256(artifact.read_bytes()).hexdigest(); order_digest = digest(feature_order())
    metadata = {"candidate_id": f"candidate:{sha[:16]}", "artifact_sha256": sha, "feature_order_digest": order_digest}
    candidate_identity.validate_candidate_identity(artifact, metadata, dict(metadata), order_digest)
    bad = dict(metadata); bad["candidate_id"] = "candidate:wrong"
    with pytest.raises(ContractError):
        candidate_identity.validate_candidate_identity(artifact, metadata, bad, order_digest)
    artifact.write_bytes(b"changed")
    with pytest.raises(ContractError, match="SHA"):
        candidate_identity.validate_candidate_identity(artifact, metadata, metadata, order_digest)


def test_candidate_identity_rejects_wrong_feature_order(tmp_path: Path):
    artifact = tmp_path / "candidate.bin"; artifact.write_bytes(b"final serialized bytes")
    sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    metadata = {"candidate_id": f"candidate:{sha[:16]}", "artifact_sha256": sha, "feature_order_digest": "a" * 64}
    with pytest.raises(ContractError, match="feature order"):
        candidate_identity.validate_candidate_identity(artifact, metadata, metadata, "b" * 64)


def test_candidate_identity_rejects_wrong_sha_external_id_and_missing_metadata(tmp_path: Path):
    artifact = tmp_path / "candidate.bin"; artifact.write_bytes(b"final serialized bytes")
    sha = hashlib.sha256(artifact.read_bytes()).hexdigest(); order_digest = digest(feature_order())
    valid = {"candidate_id": f"candidate:{sha[:16]}", "artifact_sha256": sha, "feature_order_digest": order_digest}
    wrong_sha = {**valid, "artifact_sha256": "0" * 64}
    with pytest.raises(ContractError):
        candidate_identity.validate_candidate_identity(artifact, wrong_sha, wrong_sha, order_digest)
    wrong_id = {**valid, "candidate_id": "candidate:" + "0" * 16}
    with pytest.raises(ContractError, match="candidate ID"):
        candidate_identity.validate_candidate_identity(artifact, wrong_id, wrong_id, order_digest)
    with pytest.raises(ContractError, match="fields"):
        candidate_identity.validate_candidate_identity(artifact, {"candidate_id": valid["candidate_id"]}, {"candidate_id": valid["candidate_id"]}, order_digest)


def test_cli_dry_commands_validate_without_outputs(capsys: pytest.CaptureFixture[str], tmp_path: Path):
    assert cli_main(["--json", "validate-config", "--campaign", str(CAMPAIGN)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True
    assert cli_main(["--json", "plan-campaign", "--campaign", str(CAMPAIGN)]) == 0
    assert json.loads(capsys.readouterr().out)["experiment_started"] is False
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("command", [
    "validate-config", "plan-campaign", "validate-counterfactuals", "render-compose",
    "inspect-environment", "validate-parameter-contract", "validate-capture-manifest",
    "validate-split", "build-freeze-preview", "run-technical-smoke",
])
def test_every_cli_command_has_help(command: str, capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as stopped:
        cli_module.parser().parse_args([command, "--help"])
    assert stopped.value.code == 0 and "usage:" in capsys.readouterr().out


def test_cli_remaining_dry_commands_succeed_without_side_effects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setattr(cli_module, "compose_config", lambda: "services: {}\n")
    monkeypatch.setattr(cli_module, "environment_lock", lambda *args: environment_fixture(dirty=True, resolved_images=False))
    zeek = tmp_path / "zeek"; zeek.mkdir()
    (zeek / "conn.log").write_text('{"ts":1,"duration":1,"conn_state":"SF"}\n', encoding="utf-8")
    (zeek / "http.log").write_text('{"ts":1,"method":"GET","host":"x","uri":"/","request_body_len":0}\n', encoding="utf-8")
    assert cli_main(["render-compose"]) == 0
    assert cli_main(["--json", "inspect-environment"]) == 0
    assert cli_main(["--json", "validate-counterfactuals"]) == 0
    assert cli_main(["--json", "validate-split"]) == 0
    assert cli_main(["--json", "build-freeze-preview"]) == 0
    assert cli_main(["--json", "validate-parameter-contract", "--scenario", str(PACKAGE / "config/smoke_navigation_a.json"), "--zeek-dir", str(zeek)]) == 0
    assert "services:" in capsys.readouterr().out
    assert sorted(path.name for path in tmp_path.iterdir()) == ["zeek"]


def test_cli_capture_validation_and_error_paths(tmp_path: Path):
    pcap = tmp_path / "captures/sample.pcap"; pcap.parent.mkdir(); write_pcap(pcap)
    execution = execution_event(); manifest = build_capture_manifest(capture_metadata(execution), tmp_path, execution)
    manifests_path = tmp_path / "manifests.json"; executions_path = tmp_path / "executions.json"
    write_canonical(manifests_path, [manifest]); write_canonical(executions_path, {execution["scenario_token"]: execution})
    assert cli_main(["--json", "validate-capture-manifest", "--manifest", str(manifests_path), "--dataset-root", str(tmp_path), "--executions", str(executions_path)]) == 0
    invalid = campaign(); invalid["unexpected"] = True; invalid_path = tmp_path / "invalid.json"; write_canonical(invalid_path, invalid)
    with pytest.raises(ContractError):
        cli_main(["validate-config", "--campaign", str(invalid_path)])
    with pytest.raises(ValueError, match="confirm-disposable"):
        cli_main(["run-technical-smoke", "--output-dir", str(tmp_path / "smoke")])
    with pytest.raises(ValueError, match="outside"):
        cli_main(["run-technical-smoke", "--confirm-disposable", "--output-dir", str(PACKAGE / "smoke-output")])


def test_compose_declares_common_client_sensor_and_two_real_targets():
    value = yaml.safe_load((PACKAGE / "compose.yaml").read_text(encoding="utf-8"))
    assert {"target-a", "target-b", "common-client", "sensor-capture"} <= value["services"].keys()
    assert value["services"]["sensor-capture"]["network_mode"] == "service:common-client"
    assert value["services"]["common-client"]["cap_drop"] == ["ALL"]
    assert value["services"]["sensor-capture"]["cap_add"] == ["NET_RAW", "NET_ADMIN"]
    assert "privileged" not in json.dumps(value).lower()
    assert value["services"]["target-a"]["build"]["dockerfile"] != value["services"]["target-b"]["build"]["dockerfile"]
    assert value["services"]["common-client"]["networks"] == ["validation_a", "validation_b"]
    assert "/var/run/docker.sock" not in json.dumps(value)
    assert "G:\\" not in json.dumps(value)


def test_new_campaign_path_has_no_direct_pcap_generation_or_historical_generator_import():
    source = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.rglob("*.py"))
    lowered = source.lower()
    assert "wrpcap" not in lowered and "scapy" not in lowered
    assert "create_capture" not in source
    assert "v0_3_15_4.run_campaign" not in source
    assert "v0_4_7" not in source
    assert "sensor-capture" in (PACKAGE / "pipeline.py").read_text(encoding="utf-8")


def test_baseline_plan_keeps_diagnostic_metadata_models_non_deployable():
    plans = {row["name"]: row for row in campaign()["baseline_plan"]}
    assert plans["generator_family_only"]["fixed_hyperparameters"]["diagnostic_only"] is True
    assert plans["infrastructure_only"]["fixed_hyperparameters"]["diagnostic_only"] is True
    assert plans["intended_candidate"]["training_split"] == "frozen"
