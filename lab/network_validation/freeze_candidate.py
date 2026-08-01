from __future__ import annotations

from collections import defaultdict
from typing import Any

from .contracts import BEHAVIORS, FAMILIES, ContractError, digest, validate_scenario
from .generators.family_a import FamilyA
from .generators.family_b import FamilyB
from .planning import validate_infrastructure_profiles

FREEZE_CANDIDATE_SCHEMA = "network_validation_freeze_candidate_v1"
ACCEPTANCE_CRITERIA_SCHEMA = "network_validation_acceptance_criteria_v1"
INTENSITY_BANDS = {
    "low": {"action_count": 2, "episode_duration_seconds": 4, "nominal_rate_per_second": 0.5, "spacing_ms": 2000},
    "medium": {"action_count": 6, "episode_duration_seconds": 6, "nominal_rate_per_second": 1.0, "spacing_ms": 1000},
    "high": {"action_count": 12, "episode_duration_seconds": 6, "nominal_rate_per_second": 2.0, "spacing_ms": 500},
}
BACKGROUND_POLICIES = {
    "http": {"http_requests": 1, "dns_queries": 0, "keepalive_count": 0},
    "dns": {"http_requests": 0, "dns_queries": 1, "keepalive_count": 0},
    "keepalive": {"http_requests": 0, "dns_queries": 0, "keepalive_count": 1},
    "combined": {"http_requests": 1, "dns_queries": 1, "keepalive_count": 1},
}
ACCEPTANCE_VALUES = {
    "minimum_candidate_macro_f1": 0.80,
    "maximum_false_positive_rate": 0.05,
    "minimum_per_class_recall": 0.65,
    "maximum_macro_f1_drop_unseen_generator_family": 0.10,
    "maximum_macro_f1_drop_unseen_infrastructure": 0.10,
    "maximum_macro_f1_drop_unseen_target": 0.10,
    "minimum_margin_over_infrastructure_only_baseline": 0.15,
    "minimum_margin_over_ports_services_only_baseline": 0.10,
    "minimum_margin_over_traffic_rate_only_baseline": 0.05,
    "minimum_parameter_realization_pass_rate": 0.95,
    "minimum_counterfactual_pass_rate": 0.90,
    "external_corpus_required": True,
    "minimum_external_corpus_macro_f1": 0.70,
    "maximum_external_corpus_false_positive_rate": 0.10,
    "minimum_external_per_class_recall": 0.55,
    "maximum_excluded_row_share": 0.02,
    "maximum_unresolved_required_parameter_share": 0.00,
}


def _exact(value: dict[str, Any], required: set[str]) -> None:
    if set(value) != required:
        raise ContractError("freeze-candidate fields mismatch")


def _parameter_vector(family: str, behavior: str, count: int, band: str) -> dict[str, Any]:
    ordinal = list(INTENSITY_BANDS).index(band)
    if behavior == "navigation":
        return {"path_rotation" if family == "family_a" else "phase_rotation": ordinal + 1}
    if behavior == "credential_rejection":
        return {"credential_rotation" if family == "family_a" else "session_rotation": ordinal + 2}
    if behavior == "periodic_callback":
        return {"cadence_mode": "steady" if family == "family_a" else "phased"}
    if behavior == "throttled_pressure":
        return {"burst_width" if family == "family_a" else "phase_width": ordinal + 2}
    if behavior == "service_discovery":
        if family == "family_a":
            return {"ports": list(range(10080, 10080 + count))}
        return {"port_start": 10080, "port_width": count}
    return {"path_set": "inspection_a" if family == "family_a" else "inspection_b"}


def _background_policy(behavior: str, family: str, profile_id: str, band: str) -> tuple[str, dict[str, int]]:
    family_index = ["family_a", "family_b"].index(family)
    profile_index = ["profile_a", "profile_b"].index(profile_id)
    band_index = list(INTENSITY_BANDS).index(band)
    policy_index = (family_index * 2 + profile_index + band_index) % 4
    if sorted(BEHAVIORS).index(behavior) >= 3:
        policy_index ^= 1
    name = list(BACKGROUND_POLICIES)[policy_index]
    return name, BACKGROUND_POLICIES[name]


def expand_scenarios(plan: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = plan["factorial_matrix"]
    profiles = {row["profile_id"]: row for row in plan["infrastructure_profiles"]}
    rows = []
    for behavior in matrix["behaviors"]:
        for family in matrix["generator_families"]:
            for profile_id in matrix["infrastructure_profiles"]:
                profile = profiles[profile_id]
                for band in matrix["intensity_bands"]:
                    intensity = INTENSITY_BANDS[band]
                    background_name, background_policy = _background_policy(behavior, family, profile_id, band)
                    token = f"{behavior}_{family}_{profile_id}_{band}"
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
                        "background_traffic_policy": background_policy,
                        "seed": 1000 + len(rows),
                        "campaign_token": plan["campaign_token"],
                        "infrastructure_profile": profile_id,
                        "capture_policy": {"interface": "any", "bpf": "tcp or udp port 53", "marker_copies": 2},
                    }
                    rows.append({
                        "scenario": scenario,
                        "session_token": f"session_{len(rows) + 1:03d}",
                        "intensity_band": band,
                        "background_policy": background_name,
                        "nominal_rate_per_second": intensity["nominal_rate_per_second"],
                        "target_implementation": profile["target_implementation"],
                        "target_port": profile["internal_port"],
                        "docker_network": profile["docker_network"],
                        "dns_name": profile["dns_name"],
                        "response_status_profile": profile["response_template"],
                    })
    return rows


def _scenario_index(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["scenario"]["scenario_token"]: row for row in expand_scenarios(plan)}


def counterfactual_pairs(plan: dict[str, Any]) -> list[dict[str, Any]]:
    pairs = []
    for behavior in plan["factorial_matrix"]["behaviors"]:
        pairs.append({
            "pair_id": f"same_{behavior}_different_family",
            "comparison_type": "within_behavior_generator_family",
            "left": f"{behavior}_family_a_profile_a_medium",
            "right": f"{behavior}_family_b_profile_a_medium",
            "allowed_differences": ["generator_family", "parameter_vector", "action_semantics", "background_traffic_policy"],
            "match_fields": ["behavior_type", "infrastructure_profile", "target_implementation", "target_port", "intensity_band", "action_count", "nominal_rate_per_second"],
        })
        pairs.append({
            "pair_id": f"same_{behavior}_different_infrastructure",
            "comparison_type": "within_behavior_infrastructure_profile",
            "left": f"{behavior}_family_a_profile_a_low",
            "right": f"{behavior}_family_a_profile_b_low",
            "allowed_differences": ["infrastructure_profile", "target_implementation", "target_port", "docker_network", "dns_name", "response_status_profile", "background_traffic_policy"],
            "match_fields": ["behavior_type", "generator_family", "intensity_band", "action_count", "nominal_rate_per_second"],
        })
    pairs.extend([
        {"pair_id": "same_behavior_different_paths", "comparison_type": "within_behavior_http_paths", "left": "path_inspection_family_a_profile_a_medium", "right": "path_inspection_family_b_profile_a_medium", "allowed_differences": ["generator_family", "parameter_vector", "http_paths", "background_traffic_policy"], "match_fields": ["behavior_type", "infrastructure_profile", "target_implementation", "target_port", "intensity_band", "action_count", "nominal_rate_per_second"]},
        {"pair_id": "same_behavior_different_statuses", "comparison_type": "within_behavior_response_status", "left": "credential_rejection_family_a_profile_a_medium", "right": "credential_rejection_family_a_profile_b_medium", "allowed_differences": ["infrastructure_profile", "target_implementation", "target_port", "docker_network", "dns_name", "response_status_profile", "background_traffic_policy"], "match_fields": ["behavior_type", "generator_family", "intensity_band", "action_count", "nominal_rate_per_second"]},
        {"pair_id": "same_band_different_timing", "comparison_type": "within_behavior_action_timing", "left": "periodic_callback_family_a_profile_a_high", "right": "periodic_callback_family_b_profile_a_high", "allowed_differences": ["generator_family", "parameter_vector", "action_timing", "background_traffic_policy"], "match_fields": ["behavior_type", "infrastructure_profile", "target_implementation", "target_port", "intensity_band", "action_count", "nominal_rate_per_second"]},
    ])
    cross = [
        ("different_behavior_same_port", "navigation", "credential_rejection", "profile_a", "low"),
        ("different_behavior_same_target", "navigation", "path_inspection", "profile_b", "medium"),
        ("different_behavior_same_count", "navigation", "path_inspection", "profile_a", "high"),
        ("different_behavior_same_rate", "periodic_callback", "service_discovery", "profile_b", "low"),
        ("navigation_high_intensity", "navigation", "throttled_pressure", "profile_a", "high"),
        ("path_inspection_low_intensity", "path_inspection", "navigation", "profile_b", "low"),
        ("credential_navigation_same_http_intensity", "credential_rejection", "navigation", "profile_a", "medium"),
        ("callback_discovery_same_action_count", "periodic_callback", "service_discovery", "profile_b", "medium"),
        ("pressure_navigation_same_rate", "throttled_pressure", "navigation", "profile_b", "high"),
    ]
    for pair_id, left_behavior, right_behavior, profile, band in cross:
        pairs.append({
            "pair_id": pair_id,
            "comparison_type": "cross_behavior_matched_load",
            "left": f"{left_behavior}_family_a_{profile}_{band}",
            "right": f"{right_behavior}_family_a_{profile}_{band}",
            "allowed_differences": ["behavior_type", "parameter_vector", "target_capability", "payload_size", "retry_policy", "timeout_policy", "action_semantics", "background_traffic_policy"],
            "match_fields": ["generator_family", "infrastructure_profile", "target_implementation", "target_port", "intensity_band", "action_count", "nominal_rate_per_second"],
        })
    return pairs


def _field(row: dict[str, Any], field: str) -> Any:
    scenario = row["scenario"]
    mapping = {
        "behavior_type": scenario["behavior_type"], "generator_family": scenario["generator_family"],
        "infrastructure_profile": scenario["infrastructure_profile"], "action_count": scenario["requested_request_count"],
        "background_traffic_policy": scenario["background_traffic_policy"],
    }
    return mapping[field] if field in mapping else row[field]


def validate_counterfactual_matrix(plan: dict[str, Any]) -> list[dict[str, Any]]:
    scenarios = _scenario_index(plan)
    pairs = counterfactual_pairs(plan)
    ids = set()
    for pair in pairs:
        _exact(pair, {"pair_id", "comparison_type", "left", "right", "allowed_differences", "match_fields"})
        if pair["pair_id"] in ids or pair["left"] == pair["right"] or pair["left"] not in scenarios or pair["right"] not in scenarios:
            raise ContractError("invalid freeze counterfactual reference")
        if set(pair["allowed_differences"]) & set(pair["match_fields"]):
            raise ContractError("counterfactual match and difference fields overlap")
        left, right = scenarios[pair["left"]], scenarios[pair["right"]]
        if any(_field(left, field) != _field(right, field) for field in pair["match_fields"]):
            raise ContractError(f"counterfactual invariant mismatch: {pair['pair_id']}")
        ids.add(pair["pair_id"])
    return pairs


def validate_acceptance_criteria(value: dict[str, Any]) -> dict[str, Any]:
    _exact(value, {"schema_version", "sealed", "production_approval", "values", "rules", "canonical_digest"})
    if value["schema_version"] != ACCEPTANCE_CRITERIA_SCHEMA or value["sealed"] is not False or value["production_approval"] is not False:
        raise ContractError("acceptance criteria state is invalid")
    if value["values"] != ACCEPTANCE_VALUES:
        raise ContractError("acceptance criteria values mismatch")
    required_rules = {"immutable_after_seal", "no_final_holdout_tuning", "exclusions_before_label_unlock", "external_corpus_blocks_scientific_pass", "failed_required_criterion_blocks_promotion", "scientific_pass_is_not_production_approval"}
    if set(value["rules"]) != required_rules or not all(value["rules"].values()):
        raise ContractError("acceptance criteria rules are incomplete")
    if value["canonical_digest"] != digest({key: item for key, item in value.items() if key != "canonical_digest"}):
        raise ContractError("acceptance criteria digest mismatch")
    return value


def require_criteria_digest(value: dict[str, Any], expected_digest: str) -> None:
    validate_acceptance_criteria(value)
    if value["canonical_digest"] != expected_digest:
        raise ContractError("sealed acceptance criteria changed")


def validate_freeze_candidate(plan: dict[str, Any]) -> dict[str, Any]:
    _exact(plan, {"schema_version", "campaign_token", "purpose", "technical_fixture", "execution_allowed", "feature_contract_path", "acceptance_criteria_path", "image_lock_path", "candidate_identity", "infrastructure_profiles", "factorial_matrix", "counterfactual_plan", "split_policy"})
    if plan["schema_version"] != FREEZE_CANDIDATE_SCHEMA or plan["purpose"] != "scientific_campaign_plan" or plan["technical_fixture"] is not False or plan["execution_allowed"] is not False:
        raise ContractError("freeze-candidate purpose is invalid")
    if plan["campaign_token"] != "freeze_candidate_campaign":
        raise ContractError("freeze-candidate token mismatch")
    validate_infrastructure_profiles(plan["infrastructure_profiles"])
    matrix = plan["factorial_matrix"]
    _exact(matrix, {"behaviors", "generator_families", "infrastructure_profiles", "intensity_bands", "background_assignment"})
    if set(matrix["behaviors"]) != BEHAVIORS or set(matrix["generator_families"]) != FAMILIES or set(matrix["infrastructure_profiles"]) != {"profile_a", "profile_b"} or set(matrix["intensity_bands"]) != set(INTENSITY_BANDS):
        raise ContractError("freeze-candidate factorial coverage is incomplete")
    if matrix["background_assignment"] != "orthogonal_four_policy_balance":
        raise ContractError("background assignment is not balanced")
    scenarios = expand_scenarios(plan)
    if len(scenarios) != 72:
        raise ContractError("freeze-candidate matrix must expand to 72 scenarios")
    for row in scenarios:
        validate_scenario(row["scenario"])
        family = FamilyA() if row["scenario"]["generator_family"] == "family_a" else FamilyB()
        if len(family.actions(row["scenario"])) != row["scenario"]["requested_request_count"]:
            raise ContractError("intensity action count is not realized")
    for behavior in BEHAVIORS:
        behavior_rows = [row for row in scenarios if row["scenario"]["behavior_type"] == behavior]
        counts = {name: sum(row["background_policy"] == name for row in behavior_rows) for name in BACKGROUND_POLICIES}
        if counts != {name: 3 for name in BACKGROUND_POLICIES}:
            raise ContractError("background policy is not balanced within behavior")
    for field, expected_counts in (
        ("generator_family", {"family_a": 9, "family_b": 9}),
        ("infrastructure_profile", {"profile_a": 9, "profile_b": 9}),
        ("intensity_band", {"low": 6, "medium": 6, "high": 6}),
    ):
        for name in BACKGROUND_POLICIES:
            selected = [_field(row, field) for row in scenarios if row["background_policy"] == name]
            counts = {value: selected.count(value) for value in expected_counts}
            if counts != expected_counts:
                raise ContractError(f"background policy is locked to {field}")
    _exact(plan["counterfactual_plan"], {"within_behavior_dimensions", "cross_behavior_requirements"})
    if set(plan["counterfactual_plan"]["within_behavior_dimensions"]) != {"generator_family", "infrastructure_profile", "target_implementation", "target_port", "http_paths", "response_status_profile", "action_timing"}:
        raise ContractError("within-behavior counterfactual coverage is incomplete")
    if set(plan["counterfactual_plan"]["cross_behavior_requirements"]) != {"same_port", "same_target", "same_action_count", "same_nominal_rate", "navigation_high_intensity", "path_inspection_low_intensity", "credential_navigation_same_http_intensity", "callback_discovery_same_action_count", "pressure_navigation_same_rate"}:
        raise ContractError("cross-behavior counterfactual coverage is incomplete")
    validate_counterfactual_matrix(plan)
    split = plan["split_policy"]
    _exact(split, {"unit", "group_by", "holdout_types", "selection_prohibited_fields"})
    if split["unit"] != "whole_session" or set(split["holdout_types"]) != {"unseen_generator_family", "unseen_infrastructure_profile", "unseen_target_implementation", "unseen_parameter_combinations", "counterfactual_holdout", "external_corpus"}:
        raise ContractError("freeze-candidate holdout coverage is incomplete")
    if set(split["group_by"]) != {"generator_family", "infrastructure_profile", "target_implementation", "parameter_combination", "counterfactual_pair", "session_token", "campaign_token"}:
        raise ContractError("freeze-candidate split grouping is incomplete")
    if set(split["selection_prohibited_fields"]) != {"feature_values", "labels", "metrics", "predictions"}:
        raise ContractError("split selection guard is incomplete")
    _exact(plan["candidate_identity"], {"mode", "candidate_id", "training_allowed"})
    if plan["candidate_identity"]["training_allowed"] is not False:
        raise ContractError("training must remain disabled")
    return plan


def freeze_candidate_proxy_risks(plan: dict[str, Any]) -> list[dict[str, str]]:
    validate_freeze_candidate(plan)
    rows = expand_scenarios(plan)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["scenario"]["behavior_type"]].append(row)
    risks = []
    paired = {(_scenario_index(plan)[pair["left"]]["scenario"]["behavior_type"]) for pair in counterfactual_pairs(plan)} | {(_scenario_index(plan)[pair["right"]]["scenario"]["behavior_type"]) for pair in counterfactual_pairs(plan)}
    for behavior, values in groups.items():
        dimensions = {
            "generator_family": {row["scenario"]["generator_family"] for row in values},
            "infrastructure_profile": {row["scenario"]["infrastructure_profile"] for row in values},
            "target_implementation": {row["target_implementation"] for row in values},
            "target_port": {row["target_port"] for row in values},
        }
        names = {"generator_family": "class_to_generator_family_lock", "infrastructure_profile": "class_to_infrastructure_lock", "target_implementation": "class_to_target_lock", "target_port": "class_to_port_lock"}
        for field, name in names.items():
            if len(dimensions[field]) < 2:
                risks.append({"severity": "error", "behavior_type": behavior, "risk": name})
        if behavior not in paired:
            risks.append({"severity": "error", "behavior_type": behavior, "risk": "missing_counterfactual"})
        policies = [row["background_policy"] for row in values]
        if {name: policies.count(name) for name in BACKGROUND_POLICIES} != {name: 3 for name in BACKGROUND_POLICIES}:
            risks.append({"severity": "error", "behavior_type": behavior, "risk": "unbalanced_background"})
    band_sets = {behavior: {row["intensity_band"] for row in values} for behavior, values in groups.items()}
    if len({tuple(sorted(value)) for value in band_sets.values()}) != 1 or next(iter(band_sets.values())) != set(INTENSITY_BANDS):
        risks.append({"severity": "error", "behavior_type": "all", "risk": "non_overlapping_intensity"})
    return risks


def candidate_summary(plan: dict[str, Any]) -> dict[str, Any]:
    validate_freeze_candidate(plan)
    rows = expand_scenarios(plan)
    return {
        "valid": True,
        "experiment_started": False,
        "scenario_count": len(rows),
        "matrix_digest": digest(rows),
        "behaviors": sorted({row["scenario"]["behavior_type"] for row in rows}),
        "generator_families": sorted({row["scenario"]["generator_family"] for row in rows}),
        "infrastructure_profiles": sorted({row["scenario"]["infrastructure_profile"] for row in rows}),
        "target_implementations": sorted({row["target_implementation"] for row in rows}),
        "ports": sorted({row["target_port"] for row in rows}),
        "intensity_bands": sorted({row["intensity_band"] for row in rows}),
        "counterfactual_pair_count": len(counterfactual_pairs(plan)),
        "proxy_risks": freeze_candidate_proxy_risks(plan),
    }


def holdout_support(plan: dict[str, Any]) -> dict[str, bool]:
    validate_freeze_candidate(plan)
    rows = expand_scenarios(plan)
    parameter_digests = {digest(row["scenario"]["parameter_vector"]) for row in rows}
    return {
        "unseen_generator_family": len({row["scenario"]["generator_family"] for row in rows}) >= 2,
        "unseen_infrastructure_profile": len({row["scenario"]["infrastructure_profile"] for row in rows}) >= 2,
        "unseen_target_implementation": len({row["target_implementation"] for row in rows}) >= 2,
        "unseen_parameter_combinations": len(parameter_digests) > len(BEHAVIORS),
        "counterfactual_holdout": bool(counterfactual_pairs(plan)),
        "external_corpus": "external_corpus" in plan["split_policy"]["holdout_types"],
        "whole_session": plan["split_policy"]["unit"] == "whole_session" and len({row["session_token"] for row in rows}) == len(rows),
    }
