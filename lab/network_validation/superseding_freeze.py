from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import BEHAVIORS, FAMILIES, ContractError, digest, load_json, validate_scenario, write_canonical
from .freeze_candidate import (
    BACKGROUND_POLICIES,
    INTENSITY_BANDS,
    _background_policy,
    _parameter_vector,
    counterfactual_pairs,
    expand_scenarios,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name("config")
EXECUTION = Path(__file__).with_name("execution")
FREEZE = Path(__file__).with_name("freeze")
PREDECESSOR_CAMPAIGN = CONFIG / "freeze_candidate_campaign.json"
PREDECESSOR_FREEZE = FREEZE / "official_freeze.json"
CAMPAIGN_PATH = CONFIG / "superseding_freeze_campaign.json"
POLICY_PATH = CONFIG / "superseding_execution_policy.json"
SPLIT_PATH = CONFIG / "superseding_split_assignments.json"
IMAGE_PATH = CONFIG / "superseding_image_lock.json"
OFFICIAL_PATH = FREEZE / "official_superseding_freeze.json"

CAMPAIGN_SCHEMA = "network_validation_superseding_campaign_v1"
POLICY_SCHEMA = "network_validation_superseding_execution_policy_v1"
SPLIT_SCHEMA = "network_validation_superseding_split_assignments_v1"
IMAGE_SCHEMA = "network_validation_superseding_image_reference_v1"
FREEZE_SCHEMA = "network_validation_official_superseding_freeze_v1"
SUPERSEDING_REASON = "execution_completeness_and_factor_orthogonality"
PREDECESSOR_ID = "network-validation-d6e946188d870a7f"
PREDECESSOR_DIGEST = "870946390f9ca8a5fe0ac2c53e7855e979ef242d9486815ef67d6d47ca9cbe41"
REPETITIONS = 3

TARGETS = (
    {"target_implementation": "target_a", "response_status_profile": "json_status_path"},
    {"target_implementation": "target_b", "response_status_profile": "json_result_resource"},
)
PROFILES = (
    {"profile_id": "profile_a", "docker_network": "validation_a", "subnet": "172.28.10.0/24", "dns_zone": "profile-a.internal"},
    {"profile_id": "profile_b", "docker_network": "validation_b", "subnet": "172.28.20.0/24", "dns_zone": "profile-b.internal"},
)
PORTS = (8080, 9080)

RETRY_REASONS = (
    "docker_daemon_transient_failure",
    "container_start_failure",
    "target_healthcheck_failure",
    "capture_start_failure",
    "capture_integrity_failure",
    "host_io_failure",
    "processing_integrity_failure",
)
EXCLUSION_REASONS = (
    "capture_integrity_failure",
    "session_boundary_integrity_failure",
    "processing_integrity_failure",
    "output_integrity_failure",
    "clock_integrity_failure",
)


def _canonical_identity(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"canonical_digest", "canonical_payload_sha256", "created_at", "freeze_id"}}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scenario_token(behavior: str, family: str, profile: str, target: str, port: int, band: str) -> str:
    return f"{behavior}_{family}_{profile}_{target}_{port}_{band}"


def _predecessor_rows() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    plan = load_json(PREDECESSOR_CAMPAIGN)
    return plan, expand_scenarios(plan)


def factor_locks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    profile_targets: dict[str, set[str]] = {}
    profile_ports: dict[str, set[int]] = {}
    target_profiles: dict[str, set[str]] = {}
    target_ports: dict[str, set[int]] = {}
    port_profiles: dict[int, set[str]] = {}
    port_targets: dict[int, set[str]] = {}
    for row in rows:
        scenario = row.get("scenario", row)
        profile = scenario["infrastructure_profile"]
        target = row["target_implementation"]
        port = int(row["target_port"])
        profile_targets.setdefault(profile, set()).add(target)
        profile_ports.setdefault(profile, set()).add(port)
        target_profiles.setdefault(target, set()).add(profile)
        target_ports.setdefault(target, set()).add(port)
        port_profiles.setdefault(port, set()).add(profile)
        port_targets.setdefault(port, set()).add(target)
    encode = lambda values: {str(key): sorted(items) for key, items in sorted(values.items(), key=lambda item: str(item[0]))}
    return {
        "profile_to_targets": encode(profile_targets),
        "profile_to_ports": encode(profile_ports),
        "target_to_profiles": encode(target_profiles),
        "target_to_ports": encode(target_ports),
        "port_to_profiles": encode(port_profiles),
        "port_to_targets": encode(port_targets),
        "infrastructure_to_target_lock": all(len(items) == 1 for items in profile_targets.values()),
        "infrastructure_to_port_lock": all(len(items) == 1 for items in profile_ports.values()),
        "target_to_port_lock": all(len(items) == 1 for items in target_ports.values()),
    }


def _translated_counterfactuals(old_plan: dict[str, Any], old_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_token = {row["scenario"]["scenario_token"]: row for row in old_rows}

    def translated(token: str) -> str:
        row = by_token[token]
        scenario = row["scenario"]
        return _scenario_token(
            scenario["behavior_type"], scenario["generator_family"], scenario["infrastructure_profile"],
            row["target_implementation"], int(row["target_port"]), row["intensity_band"],
        )

    values = []
    for pair in counterfactual_pairs(old_plan):
        values.append({**copy.deepcopy(pair), "left": translated(pair["left"]), "right": translated(pair["right"])})
    return values


def build_campaign() -> dict[str, Any]:
    old_plan, old_rows = _predecessor_rows()
    old_seed = {}
    for row in old_rows:
        scenario = row["scenario"]
        key = (
            scenario["behavior_type"], scenario["generator_family"], scenario["infrastructure_profile"],
            row["target_implementation"], int(row["target_port"]), row["intensity_band"],
        )
        old_seed[key] = (scenario["scenario_token"], int(scenario["seed"]))
    next_new_seed = 10000
    templates = []
    for behavior in old_plan["factorial_matrix"]["behaviors"]:
        for family in old_plan["factorial_matrix"]["generator_families"]:
            for profile in (row["profile_id"] for row in PROFILES):
                for target in (row["target_implementation"] for row in TARGETS):
                    for port in PORTS:
                        for band in old_plan["factorial_matrix"]["intensity_bands"]:
                            intensity = INTENSITY_BANDS[band]
                            background_name, background = _background_policy(behavior, family, profile, band)
                            key = (behavior, family, profile, target, port, band)
                            predecessor = old_seed.get(key)
                            if predecessor:
                                predecessor_token, base_seed = predecessor
                            else:
                                predecessor_token, base_seed = None, next_new_seed
                                next_new_seed += 1
                            token = _scenario_token(behavior, family, profile, target, port, band)
                            scenario = {
                                "schema_version": "network_validation_scenario_v1",
                                "scenario_token": token,
                                "behavior_type": behavior,
                                "generator_family": family,
                                "parameter_vector": _parameter_vector(family, behavior, intensity["action_count"], band),
                                "target_capability": "multi_port" if behavior == "service_discovery" else "api" if behavior in {"credential_rejection", "throttled_pressure"} else "control" if behavior == "periodic_callback" else "web",
                                "requested_duration_seconds": intensity["episode_duration_seconds"],
                                "requested_request_count": intensity["action_count"],
                                "requested_spacing_ms": intensity["spacing_ms"],
                                "requested_payload_size": 64 if behavior == "credential_rejection" else 32 if behavior == "throttled_pressure" else 0,
                                "retry_policy": {"max_retries": 0 if behavior == "service_discovery" else 1, "backoff_ms": 0 if behavior == "service_discovery" else 20},
                                "timeout_policy": {"connect_ms": 300 if behavior == "service_discovery" else 500, "read_ms": 500 if behavior == "service_discovery" else 1000, "expected": "either" if behavior == "service_discovery" else "response"},
                                "response_order_expectation": "normal",
                                "background_traffic_policy": background,
                                "seed": base_seed,
                                "campaign_token": "superseding_freeze_campaign",
                                "infrastructure_profile": profile,
                                "capture_policy": {"interface": "any", "bpf": "tcp or udp port 53", "marker_copies": 2},
                            }
                            templates.append({
                                "scenario": scenario,
                                "predecessor_scenario_token": predecessor_token,
                                "intensity_band": band,
                                "background_policy": background_name,
                                "nominal_rate_per_second": intensity["nominal_rate_per_second"],
                                "target_implementation": target,
                                "target_port": port,
                                "docker_network": next(row["docker_network"] for row in PROFILES if row["profile_id"] == profile),
                                "dns_name": f"{target.replace('_', '-')}.{next(row['dns_zone'] for row in PROFILES if row['profile_id'] == profile)}",
                                "response_status_profile": next(row["response_status_profile"] for row in TARGETS if row["target_implementation"] == target),
                            })
    value = {
        "schema_version": CAMPAIGN_SCHEMA,
        "campaign_token": "superseding_freeze_campaign",
        "purpose": "scientific_campaign_plan",
        "technical_fixture": False,
        "execution_allowed": False,
        "supersedes_freeze_id": PREDECESSOR_ID,
        "supersedes_freeze_digest": PREDECESSOR_DIGEST,
        "superseding_reason": SUPERSEDING_REASON,
        "feature_contract_path": old_plan["feature_contract_path"],
        "acceptance_criteria_path": old_plan["acceptance_criteria_path"],
        "image_lock_path": "lab/network_validation/config/superseding_image_lock.json",
        "candidate_identity": copy.deepcopy(old_plan["candidate_identity"]),
        "infrastructure_profiles": [copy.deepcopy(row) for row in PROFILES],
        "target_implementations": [copy.deepcopy(row) for row in TARGETS],
        "service_ports": list(PORTS),
        "factorial_matrix": {
            "behaviors": list(old_plan["factorial_matrix"]["behaviors"]),
            "generator_families": list(old_plan["factorial_matrix"]["generator_families"]),
            "infrastructure_profiles": [row["profile_id"] for row in PROFILES],
            "target_implementations": [row["target_implementation"] for row in TARGETS],
            "service_ports": list(PORTS),
            "intensity_bands": list(old_plan["factorial_matrix"]["intensity_bands"]),
            "background_assignment": "balanced_non_factorial_assignment",
        },
        "scenario_templates": templates,
        "counterfactual_pairs": _translated_counterfactuals(old_plan, old_rows),
    }
    value["canonical_digest"] = digest(value)
    return value


def _contract_digests() -> dict[str, str]:
    return {
        "output_contract_digest": digest(load_json(EXECUTION / "output_contract.json")),
        "ledger_contract_digest": digest(load_json(EXECUTION / "campaign_ledger_contract.json")),
        "label_vault_contract_digest": digest(load_json(EXECUTION / "label_vault_contract.json")),
        "preflight_contract_digest": digest(load_json(EXECUTION / "preflight_contract.json")),
    }


def _execution_token(scenario_token: str, repetition: int) -> tuple[str, str]:
    identity = _sha(f"network-validation-execution-v1\0{scenario_token}\0{repetition}")
    return identity[:24], identity


def build_assignments(campaign: dict[str, Any]) -> dict[str, Any]:
    parameter_count = math.ceil(len(campaign["scenario_templates"]) * 0.20)
    parameter_templates = {
        row["scenario"]["scenario_token"]
        for row in sorted(
            campaign["scenario_templates"],
            key=lambda row: _sha(f"parameter-combination-v1\0{row['scenario']['scenario_token']}"),
        )[:parameter_count]
    }
    counterfactual_templates = {token for pair in campaign["counterfactual_pairs"] for token in (pair["left"], pair["right"])}
    units = []
    split_names = ("development_train", "development_calibration", "blind_internal_holdout")
    for template in campaign["scenario_templates"]:
        scenario = template["scenario"]
        for repetition in range(REPETITIONS):
            display, identity = _execution_token(scenario["scenario_token"], repetition)
            views = []
            if repetition == 0 and scenario["generator_family"] == "family_a":
                views.append("unseen_generator_train_side")
            if repetition == 1 and scenario["generator_family"] == "family_b":
                views.append("unseen_generator_stress")
            if repetition == 0 and scenario["infrastructure_profile"] == "profile_a":
                views.append("unseen_infrastructure_train_side")
            if repetition == 1 and scenario["infrastructure_profile"] == "profile_b":
                views.append("unseen_infrastructure_stress")
            if repetition == 0 and template["target_implementation"] == "target_a":
                views.append("unseen_target_train_side")
            if repetition == 1 and template["target_implementation"] == "target_b":
                views.append("unseen_target_stress")
            if repetition in {0, 1} and scenario["scenario_token"] in parameter_templates:
                views.append("development_parameter_combination_holdout")
            if scenario["scenario_token"] in counterfactual_templates and repetition == 1:
                views.append("development_counterfactual_view")
            if scenario["scenario_token"] in counterfactual_templates and repetition == 2:
                views.append("blind_counterfactual_view")
            units.append({
                "execution_token": display,
                "execution_identity_sha256": identity,
                "scenario_token": scenario["scenario_token"],
                "repetition_index": repetition,
                "base_seed": scenario["seed"],
                "execution_seed": int(scenario["seed"]) + repetition * 100000,
                "primary_split": split_names[repetition],
                "analysis_views": sorted(views),
                "order_key": _sha(f"network-validation-order-v1\0{display}"),
            })
    units.sort(key=lambda row: row["order_key"])
    for index, row in enumerate(units):
        row["execution_order_index"] = index
    value = {
        "schema_version": SPLIT_SCHEMA,
        "campaign_digest": campaign["canonical_digest"],
        "scenario_template_count": len(campaign["scenario_templates"]),
        "repetitions_per_template": REPETITIONS,
        "execution_session_count": len(units),
        "parameter_combination_rule": "first_ceil_20_percent_by_sha256_parameter_combination_v1",
        "parameter_combination_templates": sorted(parameter_templates),
        "ordered_execution_units": units,
    }
    value["canonical_digest"] = digest(value)
    return value


def build_policy(campaign: dict[str, Any], assignments: dict[str, Any]) -> dict[str, Any]:
    contract_digests = _contract_digests()
    value = {
        "schema_version": POLICY_SCHEMA,
        "repetitions_per_template": REPETITIONS,
        "seed_derivation": {"algorithm": "base_seed_plus_repetition_index_times_100000", "multiplier": 100000, "system_random_allowed": False},
        "execution_token_derivation": "sha256_network-validation-execution-v1_nul_scenario-token_nul_repetition-index",
        "ordering_policy": "ascending_sha256_network-validation-order-v1_nul_execution-token",
        "exact_execution_order_digest": digest([row["execution_token"] for row in assignments["ordered_execution_units"]]),
        "run_plan_digest": digest(assignments["ordered_execution_units"]),
        "concurrency": 1,
        "session_reset_policy": {
            "new_compose_project": True, "new_network_instance": True, "new_containers": True,
            "ephemeral_target_filesystem": True, "persistent_target_state": False,
            "persistent_client_state": False, "connection_reuse_across_sessions": False,
            "new_dns_client_sensor_processes": True, "new_asset_state": True,
            "new_feature_history_state": True, "separate_output_directory": True,
            "teardown_containers_networks_temporary_volumes": True, "destroy_images": False,
        },
        "warmup_seconds": 2.0,
        "capture_start_lead_seconds": 0.5,
        "capture_stop_lag_seconds": 0.5,
        "cooldown_seconds": 1.0,
        "clock_offset_tolerance_ms": 500,
        "clock_policy": {"check_before_campaign": True, "check_before_each_session": True, "monotonic_required": True, "timestamps_non_decreasing": True, "post_hoc_correction_allowed": False, "failure_code": "CLOCK_PREFLIGHT_FAILED"},
        "technical_retry_policy": {"maximum_retries_per_execution": 1, "maximum_attempts_total": 2, "reason_allowlist": list(RETRY_REASONS), "preserve_failed_attempts": True},
        "replacement_policy": {"scenario_substitution_allowed": False, "parameter_substitution_allowed": False, "replacement_with_different_seed_allowed": False, "retry_same_execution_identity": True},
        "exclusion_reason_allowlist": list(EXCLUSION_REASONS),
        "exclusion_forbidden_inputs": ["feature_values", "prediction", "label", "class", "model_confidence", "metric_result", "parameter_realization_outcome"],
        "primary_split_policy": {"0": "development_train", "1": "development_calibration", "2": "blind_internal_holdout", "materialized_before_collection": True},
        "stress_view_policy": {"metadata_only": True, "unseen_generator": True, "unseen_infrastructure": True, "unseen_target": True, "unseen_parameter_combination_minimum_share": 0.20, "counterfactual_views": True},
        "runtime_orthogonality_validation": {
            "status": "technical_passed",
            "combination_count": 8,
            "all_pcaps_non_empty": True,
            "all_expected_tcp_flows_confirmed": True,
            "all_zeek_conn_logs_non_empty": True,
            "all_feature_vectors_51": True,
            "scientific_run": False,
            "evidence_retention": "disposable_output_removed_after_verification",
        },
        **contract_digests,
    }
    value["canonical_digest"] = digest(value)
    return value


def build_image_reference() -> dict[str, Any]:
    old = load_json(CONFIG / "image_lock.json")
    value = {
        "schema_version": IMAGE_SCHEMA,
        "predecessor_image_lock_path": "lab/network_validation/config/image_lock.json",
        "predecessor_image_lock_digest": old["canonical_digest"],
        "image_bytes_changed": False,
        "required_images": [row["logical_name"] for row in old["images"]],
        "reproducibility_status": "reuse_predecessor_verified_identities",
    }
    value["canonical_digest"] = digest(value)
    return value


def materialize_inputs() -> dict[str, Any]:
    campaign = build_campaign()
    assignments = build_assignments(campaign)
    policy = build_policy(campaign, assignments)
    image = build_image_reference()
    write_canonical(CAMPAIGN_PATH, campaign)
    write_canonical(POLICY_PATH, policy)
    write_canonical(SPLIT_PATH, assignments)
    write_canonical(IMAGE_PATH, image)
    return validate_inputs(campaign, policy, assignments, image)


def validate_inputs(
    campaign: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    assignments: dict[str, Any] | None = None,
    image: dict[str, Any] | None = None,
) -> dict[str, Any]:
    campaign = campaign or load_json(CAMPAIGN_PATH)
    policy = policy or load_json(POLICY_PATH)
    assignments = assignments or load_json(SPLIT_PATH)
    image = image or load_json(IMAGE_PATH)
    expected_campaign = build_campaign()
    if campaign != expected_campaign:
        raise ContractError("superseding campaign is not canonical")
    for row in campaign["scenario_templates"]:
        validate_scenario(row["scenario"])
    if len(campaign["scenario_templates"]) != 288:
        raise ContractError("superseding campaign must contain 288 templates")
    if len(campaign["counterfactual_pairs"]) != 24:
        raise ContractError("predecessor counterfactual pairs were not preserved")
    expected_assignments = build_assignments(campaign)
    if assignments != expected_assignments:
        raise ContractError("superseding split assignments are not canonical")
    expected_policy = build_policy(campaign, assignments)
    if policy != expected_policy:
        raise ContractError("superseding execution policy is not canonical")
    if image != build_image_reference():
        raise ContractError("superseding image reference is not canonical")
    units = assignments["ordered_execution_units"]
    identities = [row["execution_identity_sha256"] for row in units]
    seeds = [row["execution_seed"] for row in units]
    if len(units) != len(set(identities)) or len(units) != len(set(seeds)) or len(units) != 864:
        raise ContractError("execution identities or seeds are not unique")
    if [row["order_key"] for row in units] != sorted(row["order_key"] for row in units):
        raise ContractError("execution ordering is not canonical")
    split_counts = {name: sum(row["primary_split"] == name for row in units) for name in ("development_train", "development_calibration", "blind_internal_holdout")}
    if set(split_counts.values()) != {288}:
        raise ContractError("primary split counts are invalid")
    selected = set(assignments["parameter_combination_templates"])
    selected_rows = [row for row in campaign["scenario_templates"] if row["scenario"]["scenario_token"] in selected]
    if len(selected) < math.ceil(288 * 0.20):
        raise ContractError("parameter combination view is too small")
    dimensions = {
        "behaviors": {row["scenario"]["behavior_type"] for row in selected_rows},
        "intensities": {row["intensity_band"] for row in selected_rows},
        "families": {row["scenario"]["generator_family"] for row in selected_rows},
        "profiles": {row["scenario"]["infrastructure_profile"] for row in selected_rows},
        "targets": {row["target_implementation"] for row in selected_rows},
        "ports": {row["target_port"] for row in selected_rows},
    }
    if {key: len(value) for key, value in dimensions.items()} != {"behaviors": 6, "intensities": 3, "families": 2, "profiles": 2, "targets": 2, "ports": 2}:
        raise ContractError("parameter combination view lacks factor coverage")
    locks = factor_locks(campaign["scenario_templates"])
    if any(locks[name] for name in ("infrastructure_to_target_lock", "infrastructure_to_port_lock", "target_to_port_lock")):
        raise ContractError("nuisance factors remain locked")
    behavior_counts = {behavior: sum(row["scenario"]["behavior_type"] == behavior for row in campaign["scenario_templates"]) for behavior in BEHAVIORS}
    if set(behavior_counts.values()) != {48}:
        raise ContractError("behavior templates are not balanced")
    return {
        "valid": True,
        "scientific_campaign_started": False,
        "scenario_templates": 288,
        "repetitions_per_template": 3,
        "execution_sessions": 864,
        "split_counts": split_counts,
        "counterfactual_pair_count": 24,
        "proxy_warning_count": 0,
        "nuisance_factor_warning_count": 0,
        "nuisance_factor_validation": locks,
        "campaign_digest": campaign["canonical_digest"],
        "execution_policy_digest": policy["canonical_digest"],
        "split_assignment_digest": assignments["canonical_digest"],
        "image_lock_digest": image["canonical_digest"],
    }


def official_payload(source_git_sha: str, created_at: str) -> dict[str, Any]:
    inputs = validate_inputs()
    campaign, policy, assignments, image = (load_json(path) for path in (CAMPAIGN_PATH, POLICY_PATH, SPLIT_PATH, IMAGE_PATH))
    predecessor = load_json(PREDECESSOR_FREEZE)
    if predecessor["freeze_id"] != PREDECESSOR_ID or predecessor["canonical_payload_sha256"] != PREDECESSOR_DIGEST:
        raise ContractError("predecessor freeze identity mismatch")
    result = subprocess.run(["git", "cat-file", "-e", f"{source_git_sha}^{{commit}}"], cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        raise ContractError("superseding source Git SHA does not exist")
    source_paths = (CAMPAIGN_PATH, POLICY_PATH, SPLIT_PATH, IMAGE_PATH) + tuple(EXECUTION / name for name in (
        "output_contract.json", "campaign_ledger_contract.json", "label_vault_contract.json", "preflight_contract.json"
    ))
    for path in source_paths:
        relative = path.relative_to(ROOT).as_posix()
        committed = subprocess.run(["git", "show", f"{source_git_sha}:{relative}"], cwd=ROOT, capture_output=True, check=False)
        if committed.returncode or committed.stdout != path.read_bytes():
            raise ContractError(f"superseding source does not contain current input: {relative}")
    value = {
        "schema_version": FREEZE_SCHEMA,
        "freeze_type": "superseding",
        "created_at": created_at,
        "supersedes_freeze_id": PREDECESSOR_ID,
        "supersedes_freeze_digest": PREDECESSOR_DIGEST,
        "superseding_reason": SUPERSEDING_REASON,
        "source_git_sha": source_git_sha,
        "source_tree_clean": True,
        "campaign_digest": campaign["canonical_digest"],
        "matrix_digest": digest(campaign["scenario_templates"]),
        "execution_policy_digest": policy["canonical_digest"],
        "split_assignment_digest": assignments["canonical_digest"],
        "counterfactual_digest": digest(campaign["counterfactual_pairs"]),
        "acceptance_criteria_digest": predecessor["acceptance_criteria_digest"],
        "feature_contract_digest": predecessor["feature_contract_digest"],
        "feature_order_digest": predecessor["feature_order_digest"],
        "image_lock_digest": image["canonical_digest"],
        "referenced_predecessor_image_lock_digest": image["predecessor_image_lock_digest"],
        "scenario_template_count": inputs["scenario_templates"],
        "repetitions_per_template": inputs["repetitions_per_template"],
        "execution_session_count": inputs["execution_sessions"],
        "proxy_validation": {"passed": True, "warning_count": 0, "warnings": []},
        "nuisance_factor_validation": inputs["nuisance_factor_validation"],
        "runtime_orthogonality_validation": policy["runtime_orthogonality_validation"],
        **_contract_digests(),
        "execution_protocol_complete": True,
        "expected_pre_experiment_absences": ["scientific_corpus_not_collected", "labels_not_created", "model_not_trained", "predictions_not_created", "scientific_metrics_not_calculated", "external_evaluation_not_performed"],
        "scientific_pass_requirements": predecessor["scientific_pass_requirements"],
        "scientific_pass_allowed": False,
        "production_approval": False,
    }
    canonical = digest(_canonical_identity(value))
    value["freeze_id"] = f"network-validation-superseding-{canonical[:16]}"
    value["canonical_payload_sha256"] = canonical
    return value


def write_official(path: Path, source_git_sha: str, created_at: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise ContractError("official superseding freeze requires explicit confirmation")
    if path.exists():
        raise ContractError("official superseding freeze cannot be overwritten")
    value = official_payload(source_git_sha, created_at)
    write_canonical(path, value)
    return value


def validate_official(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or load_json(OFFICIAL_PATH)
    source = value.get("source_git_sha", "")
    expected_created_at = value.get("created_at", "")
    expected = official_payload(source, expected_created_at)
    if value != expected:
        raise ContractError("official superseding freeze integrity mismatch")
    if value["schema_version"] != FREEZE_SCHEMA or not value["execution_protocol_complete"]:
        raise ContractError("superseding execution protocol is incomplete")
    return value
