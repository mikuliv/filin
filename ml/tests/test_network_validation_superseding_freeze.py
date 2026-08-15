from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from lab.network_validation.contracts import ContractError, load_json
from lab.network_validation.superseding_freeze import (
    CAMPAIGN_PATH,
    IMAGE_PATH,
    POLICY_PATH,
    PREDECESSOR_FREEZE,
    SPLIT_PATH,
    build_assignments,
    build_campaign,
    build_image_reference,
    build_policy,
    factor_locks,
    validate_inputs,
)


ROOT = Path(__file__).resolve().parents[2]


def inputs() -> tuple[dict, dict, dict, dict]:
    return tuple(load_json(path) for path in (CAMPAIGN_PATH, POLICY_PATH, SPLIT_PATH, IMAGE_PATH))  # type: ignore[return-value]


def test_predecessor_freeze_is_byte_for_byte_unchanged() -> None:
    assert hashlib.sha256(PREDECESSOR_FREEZE.read_bytes()).hexdigest() == "a16155888673f65faadb11f8a6fba081fadf78f861794f52c600d214cd58eb58"


def test_superseding_inputs_are_canonical_and_complete() -> None:
    campaign, policy, assignments, image = inputs()
    result = validate_inputs(campaign, policy, assignments, image)
    assert result["valid"] is True and result["scientific_campaign_started"] is False
    assert (result["scenario_templates"], result["repetitions_per_template"], result["execution_sessions"]) == (288, 3, 864)
    assert result["split_counts"] == {"development_train": 288, "development_calibration": 288, "blind_internal_holdout": 288}
    assert result["counterfactual_pair_count"] == 24
    assert result["proxy_warning_count"] == result["nuisance_factor_warning_count"] == 0


def test_full_factorial_matrix_has_no_nuisance_locks_and_is_balanced() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    locks = factor_locks(campaign["scenario_templates"])
    assert locks["infrastructure_to_target_lock"] is False
    assert locks["infrastructure_to_port_lock"] is False
    assert locks["target_to_port_lock"] is False
    assert all(len(values) == 2 for name, values in locks.items() if name.endswith(("targets", "ports", "profiles")))
    for behavior in {row["scenario"]["behavior_type"] for row in campaign["scenario_templates"]}:
        rows = [row for row in campaign["scenario_templates"] if row["scenario"]["behavior_type"] == behavior]
        assert len(rows) == 48
        assert {name: sum(row["background_policy"] == name for row in rows) for name in ("http", "dns", "keepalive", "combined")} == {name: 12 for name in ("http", "dns", "keepalive", "combined")}


def test_execution_tokens_seeds_and_order_are_unique_and_deterministic() -> None:
    campaign, policy, assignments, _ = inputs()
    units = assignments["ordered_execution_units"]
    assert len({row["execution_token"] for row in units}) == 864
    assert len({row["execution_identity_sha256"] for row in units}) == 864
    assert len({row["execution_seed"] for row in units}) == 864
    assert [row["order_key"] for row in units] == sorted(row["order_key"] for row in units)
    assert assignments == build_assignments(campaign)
    assert policy == build_policy(campaign, assignments)
    assert all(row["execution_seed"] == row["base_seed"] + row["repetition_index"] * 100000 for row in units)


def test_predecessor_base_seeds_are_preserved() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    preserved = [row for row in campaign["scenario_templates"] if row["predecessor_scenario_token"]]
    assert len(preserved) == 72
    assert sorted(row["scenario"]["seed"] for row in preserved) == list(range(1000, 1072))


def test_primary_and_stress_views_are_materialized_before_collection() -> None:
    campaign, _, assignments, _ = inputs()
    units = assignments["ordered_execution_units"]
    assert all(row["primary_split"] == ("development_train", "development_calibration", "blind_internal_holdout")[row["repetition_index"]] for row in units)
    assert len(assignments["parameter_combination_templates"]) >= 58
    selected = set(assignments["parameter_combination_templates"])
    rows = [row for row in campaign["scenario_templates"] if row["scenario"]["scenario_token"] in selected]
    assert len({row["scenario"]["behavior_type"] for row in rows}) == 6
    assert len({row["intensity_band"] for row in rows}) == 3
    assert any("development_counterfactual_view" in row["analysis_views"] for row in units)
    assert any("blind_counterfactual_view" in row["analysis_views"] for row in units)


def test_execution_policy_freezes_reset_timing_retry_and_exclusion() -> None:
    policy = load_json(POLICY_PATH)
    assert policy["concurrency"] == 1 and policy["repetitions_per_template"] == 3
    assert policy["warmup_seconds"] == 2.0
    assert policy["capture_start_lead_seconds"] == policy["capture_stop_lag_seconds"] == 0.5
    assert policy["cooldown_seconds"] == 1.0 and policy["clock_offset_tolerance_ms"] == 500
    assert policy["session_reset_policy"]["new_compose_project"] is True
    assert policy["technical_retry_policy"]["maximum_retries_per_execution"] == 1
    assert "prediction_bad" not in policy["technical_retry_policy"]["reason_allowlist"]
    assert "parameter_realization_failed" not in policy["exclusion_reason_allowlist"]
    assert policy["replacement_policy"]["scenario_substitution_allowed"] is False
    assert policy["runtime_orthogonality_validation"] == {
        "status": "technical_passed",
        "combination_count": 8,
        "all_pcaps_non_empty": True,
        "all_expected_tcp_flows_confirmed": True,
        "all_zeek_conn_logs_non_empty": True,
        "all_feature_vectors_51": True,
        "scientific_run": False,
        "evidence_retention": "disposable_output_removed_after_verification",
    }


def test_contract_and_image_digests_are_frozen_without_image_changes() -> None:
    policy = load_json(POLICY_PATH)
    assert all(policy[name].isalnum() and len(policy[name]) == 64 for name in (
        "output_contract_digest", "ledger_contract_digest", "label_vault_contract_digest", "preflight_contract_digest"
    ))
    image = load_json(IMAGE_PATH)
    assert image == build_image_reference()
    assert image["image_bytes_changed"] is False
    assert image["predecessor_image_lock_digest"] == "425fbb7ec0ebedffead965d2fb5b8c17bbeb74d5a0cc43e5e9c9640a73b92981"


def test_tampering_is_detected() -> None:
    campaign, policy, assignments, image = inputs()
    changed = copy.deepcopy(assignments)
    changed["ordered_execution_units"][0]["execution_seed"] += 1
    with pytest.raises(ContractError, match="canonical"):
        validate_inputs(campaign, policy, changed, image)
    changed_campaign = copy.deepcopy(campaign)
    changed_campaign["scenario_templates"][0]["target_port"] = 9999
    with pytest.raises(ContractError, match="canonical"):
        validate_inputs(changed_campaign, policy, assignments, image)


def test_builder_is_idempotent() -> None:
    assert load_json(CAMPAIGN_PATH) == build_campaign()
