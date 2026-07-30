from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any

from .contracts import ContractError, validate_campaign
from .generators.family_a import FamilyA
from .generators.family_b import FamilyB


def validate_infrastructure_profiles(profiles: list[dict[str, Any]]) -> None:
    required = {"profile_id", "docker_network", "subnet", "dns_name", "target_implementation", "internal_port", "response_template", "service_configuration"}
    if len(profiles) < 2:
        raise ContractError("at least two infrastructure profiles are required")
    for profile in profiles:
        if set(profile) != required:
            raise ContractError("invalid infrastructure profile fields")
        if not 1 <= int(profile["internal_port"]) <= 65535:
            raise ContractError("invalid internal port")
    if len({profile["profile_id"] for profile in profiles}) != len(profiles):
        raise ContractError("duplicate infrastructure profile")
    for field in ("docker_network", "subnet", "dns_name", "target_implementation", "internal_port", "response_template"):
        if len({str(profile[field]) for profile in profiles}) < 2:
            raise ContractError(f"infrastructure profiles do not differ by {field}")


def validate_counterfactuals(campaign: dict[str, Any]) -> None:
    scenarios = {row["scenario_token"]: row for row in campaign["scenarios"]}
    pair_ids = set()
    for pair in campaign["counterfactual_pairs"]:
        if set(pair) != {"pair_id", "left", "right", "controlled_factor"}:
            raise ContractError("invalid counterfactual pair")
        if pair["pair_id"] in pair_ids or pair["left"] not in scenarios or pair["right"] not in scenarios or pair["left"] == pair["right"]:
            raise ContractError("invalid counterfactual references")
        if pair["controlled_factor"] != "generator_family":
            raise ContractError("unsupported concrete counterfactual factor")
        left, right = scenarios[pair["left"]], scenarios[pair["right"]]
        invariant_fields = {
            "behavior_type", "target_capability", "requested_duration_seconds",
            "requested_request_count", "requested_spacing_ms", "requested_payload_size",
            "retry_policy", "timeout_policy", "response_order_expectation",
            "background_traffic_policy", "seed", "campaign_token",
            "infrastructure_profile", "capture_policy",
        }
        if any(left[field] != right[field] for field in invariant_fields):
            raise ContractError("counterfactual pair changes an invariant field")
        if left["generator_family"] == right["generator_family"]:
            raise ContractError("counterfactual pair does not change generator family")
        pair_ids.add(pair["pair_id"])
    if not pair_ids:
        raise ContractError("counterfactual pairs are required")


def proxy_risks(campaign: dict[str, Any]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scenario in campaign["scenarios"]:
        groups[scenario["behavior_type"]].append(scenario)
    risks = []
    scenarios = {row["scenario_token"]: row for row in campaign["scenarios"]}
    profiles = {row["profile_id"]: row for row in campaign["infrastructure_profiles"]}
    paired_behaviors = {
        scenarios[pair["left"]]["behavior_type"]
        for pair in campaign["counterfactual_pairs"]
        if pair.get("left") in scenarios and pair.get("right") in scenarios
    }
    for behavior, rows in groups.items():
        checks = {
            "generator_family": {row["generator_family"] for row in rows},
            "infrastructure_profile": {row["infrastructure_profile"] for row in rows},
            "target_implementation": {profiles[row["infrastructure_profile"]]["target_implementation"] for row in rows},
            "port": {profiles[row["infrastructure_profile"]]["internal_port"] for row in rows},
            "request_intensity": {(row["requested_request_count"], row["requested_spacing_ms"]) for row in rows},
        }
        names = {
            "generator_family": "class_to_family_lock",
            "infrastructure_profile": "class_to_infrastructure_lock",
            "target_implementation": "class_to_target_lock",
            "port": "class_to_port_lock",
        }
        for field, risk in names.items():
            if len(checks[field]) == 1:
                risks.append({"severity": "warning", "behavior_type": behavior, "risk": risk})
        if behavior not in paired_behaviors:
            risks.append({"severity": "error", "behavior_type": behavior, "risk": "missing_counterfactual"})
        if any(sum(row["background_traffic_policy"].values()) == 0 for row in rows):
            risks.append({"severity": "error", "behavior_type": behavior, "risk": "missing_background"})
        if any("user_agent" in row for row in rows):
            risks.append({"severity": "error", "behavior_type": behavior, "risk": "unique_user_agent"})
        if any("technical_headers" in row for row in rows):
            risks.append({"severity": "error", "behavior_type": behavior, "risk": "unique_technical_header"})
        for row in rows:
            family = FamilyA() if row["generator_family"] == "family_a" else FamilyB()
            original = family.actions(row)
            changed = False
            for key, value in row["parameter_vector"].items():
                probe = copy.deepcopy(row)
                if isinstance(value, bool):
                    probe["parameter_vector"][key] = not value
                elif isinstance(value, int):
                    probe["parameter_vector"][key] = value + 1
                elif isinstance(value, str):
                    probe["parameter_vector"][key] = value + "_probe"
                elif isinstance(value, list) and value:
                    probe["parameter_vector"][key] = list(reversed(value))
                else:
                    continue
                if family.actions(probe) != original:
                    changed = True
                    break
            if not changed:
                risks.append({"severity": "error", "behavior_type": behavior, "risk": "unused_parameter_vector"})
                break
    intensities = defaultdict(set)
    for scenario in campaign["scenarios"]:
        intensities[scenario["behavior_type"]].add((scenario["requested_request_count"], scenario["requested_spacing_ms"]))
    if len({value for values in intensities.values() for value in values}) == sum(len(values) for values in intensities.values()):
        risks.append({"severity": "warning", "behavior_type": "all", "risk": "non_overlapping_intensity"})
    return risks


def plan_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    validate_campaign(campaign)
    validate_infrastructure_profiles(campaign["infrastructure_profiles"])
    profile_ids = {row["profile_id"] for row in campaign["infrastructure_profiles"]}
    if any(row["infrastructure_profile"] not in profile_ids for row in campaign["scenarios"]):
        raise ContractError("scenario references an unknown infrastructure profile")
    validate_counterfactuals(campaign)
    return {"campaign_token": campaign["campaign_token"], "technical_fixture": True, "scenario_count": len(campaign["scenarios"]), "generator_families": sorted({row["generator_family"] for row in campaign["scenarios"]}), "infrastructure_profiles": sorted({row["infrastructure_profile"] for row in campaign["scenarios"]}), "counterfactual_requirements": sorted(campaign["counterfactual_requirements"]), "proxy_risks": proxy_risks(campaign), "experiment_started": False}


def validate_split(assignments: list[dict[str, Any]], policy: dict[str, Any]) -> None:
    policy_fields = {"unit", "group_by", "holdout_generator_family", "holdout_infrastructure", "holdout_target", "fixture_assignments"}
    if set(policy) != policy_fields or policy["unit"] != "whole_session":
        raise ContractError("invalid split policy")
    if set(policy["group_by"]) != {"generator_family", "infrastructure_profile", "target_implementation", "session_token", "campaign_token"}:
        raise ContractError("split grouping is incomplete")
    if any(not isinstance(policy[field], bool) for field in ("holdout_generator_family", "holdout_infrastructure", "holdout_target")):
        raise ContractError("split holdout flags must be boolean")
    required = {"session_token", "campaign_token", "generator_family", "infrastructure_profile", "target_implementation", "split"}
    if not assignments:
        raise ContractError("split assignments are required")
    for row in assignments:
        if set(row) != required:
            raise ContractError("invalid split row")
        if row["split"] not in {"training", "calibration", "internal_audit", "final_holdout"}:
            raise ContractError("unknown split")
    sessions = [str(row["session_token"]) for row in assignments]
    if len(sessions) != len(set(sessions)):
        raise ContractError("session_token overlaps splits")
    final = [row for row in assignments if row["split"] == "final_holdout"]
    development = [row for row in assignments if row["split"] != "final_holdout"]
    for field, enabled in {
        "generator_family": policy.get("holdout_generator_family"),
        "infrastructure_profile": policy.get("holdout_infrastructure"),
        "target_implementation": policy.get("holdout_target"),
    }.items():
        if enabled and ({row[field] for row in final} & {row[field] for row in development}):
            raise ContractError(f"{field} overlaps final holdout")
    if not final or not development:
        raise ContractError("development and final holdout assignments are required")
