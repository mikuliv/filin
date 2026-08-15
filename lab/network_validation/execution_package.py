from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .contracts import ContractError, digest, load_json
from .freeze_candidate import expand_scenarios, freeze_candidate_proxy_risks, validate_freeze_candidate


EXECUTION_PACKAGE_SCHEMA = "network_validation_execution_package_preview_v1"
BLOCKED_STATUS = "EXECUTION_PACKAGE_BLOCKED_BY_FREEZE_GAP"
CONTRACT_DIR = Path(__file__).with_name("execution")

REQUIRED_CONTRACTS = {
    "campaign_ledger": "campaign_ledger_contract.json",
    "label_vault": "label_vault_contract.json",
    "output": "output_contract.json",
    "preflight": "preflight_contract.json",
}

# A missing item remains a blocker until it is present in a superseding freeze.
EXECUTION_FIELDS: tuple[dict[str, Any], ...] = (
    {"field": "scenario_definitions", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "behavior and traffic semantics"},
    {"field": "scenario_template_count", "frozen": True, "source": "seal_preconditions.scenario_count", "scientific_significance": "matrix coverage"},
    {"field": "generator_family", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "generator diversity"},
    {"field": "infrastructure_profile", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "infrastructure diversity"},
    {"field": "target_implementation", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "target diversity"},
    {"field": "intensity", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "traffic distribution"},
    {"field": "background_policy", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "background distribution"},
    {"field": "scenario_parameter_vectors", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "scenario realization"},
    {"field": "scientific_seed_values", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "randomized action realization"},
    {"field": "session_tokens", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "session grouping"},
    {"field": "counterfactual_pairs", "frozen": True, "source": "counterfactual_plan_digest", "scientific_significance": "proxy controls"},
    {"field": "feature_contract_and_order", "frozen": True, "source": "feature_contract_digest, feature_order_digest", "scientific_significance": "model input contract"},
    {"field": "acceptance_criteria", "frozen": True, "source": "acceptance_criteria_digest", "scientific_significance": "decision thresholds"},
    {"field": "image_identities", "frozen": True, "source": "image_lock_digest", "scientific_significance": "runtime reproducibility"},
    {"field": "scenario_action_retry", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "traffic behavior"},
    {"field": "scenario_timeouts", "frozen": True, "source": "campaign_matrix_digest", "scientific_significance": "traffic behavior"},
    {"field": "scientific_repetition_policy", "frozen": False, "source": "absent", "scientific_significance": "sample size and variance"},
    {"field": "execution_order_policy", "frozen": False, "source": "absent", "scientific_significance": "carry-over and temporal bias"},
    {"field": "execution_concurrency_policy", "frozen": False, "source": "absent", "scientific_significance": "resource contention and cross-traffic"},
    {"field": "session_isolation_reset_policy", "frozen": False, "source": "absent", "scientific_significance": "cross-session carry-over"},
    {"field": "warmup_and_cooldown_policy", "frozen": False, "source": "absent", "scientific_significance": "boundary contamination"},
    {"field": "capture_start_lead_and_stop_lag", "frozen": False, "source": "absent", "scientific_significance": "capture completeness"},
    {"field": "clock_offset_tolerance", "frozen": False, "source": "absent", "scientific_significance": "event and label alignment"},
    {"field": "campaign_retry_and_replacement_policy", "frozen": False, "source": "absent", "scientific_significance": "selection bias"},
    {"field": "exclusion_reason_allowlist", "frozen": False, "source": "maximum share only", "scientific_significance": "selection bias"},
    {"field": "exact_split_assignments", "frozen": False, "source": "split policy without assignments", "scientific_significance": "blind evaluation and leakage"},
    {"field": "output_and_session_integrity_schema", "frozen": False, "source": "partial runtime structures only", "scientific_significance": "corpus completeness and auditability"},
)


def _contract_payloads(contract_dir: Path = CONTRACT_DIR) -> dict[str, dict[str, Any]]:
    return {name: load_json(contract_dir / filename) for name, filename in REQUIRED_CONTRACTS.items()}


def audit_execution_readiness(campaign: dict[str, Any], official_freeze: dict[str, Any]) -> dict[str, Any]:
    validate_freeze_candidate(campaign)
    rows = expand_scenarios(campaign)
    risks = freeze_candidate_proxy_risks(campaign)
    gaps = [row["field"] for row in EXECUTION_FIELDS if not row["frozen"]]
    if official_freeze.get("seal_preconditions", {}).get("scenario_count") != 72:
        gaps.append("official_scenario_count_mismatch")
    if len(rows) != 72 or len({row["scenario"]["scenario_token"] for row in rows}) != 72:
        gaps.append("scenario_matrix_not_72_unique_templates")
    if len({row["session_token"] for row in rows}) != 72:
        gaps.append("session_tokens_not_unique")
    if official_freeze.get("seal_preconditions", {}).get("counterfactual_pair_count") != 24:
        gaps.append("official_counterfactual_count_mismatch")
    if risks:
        gaps.append("proxy_validation_not_clean")
    return {
        "status": BLOCKED_STATUS if gaps else "EXECUTION_PACKAGE_CANDIDATE_READY",
        "complete_for_execution": not gaps,
        "execution_allowed": False,
        "official_freeze_id": official_freeze.get("freeze_id"),
        "official_freeze_digest": official_freeze.get("canonical_payload_sha256"),
        "scenario_templates": len(rows),
        "unique_session_tokens": len({row["session_token"] for row in rows}),
        "counterfactual_pairs": official_freeze.get("seal_preconditions", {}).get("counterfactual_pair_count"),
        "proxy_warning_count": len(risks),
        "fields": [copy.deepcopy(row) | {"required_before_execution": not row["frozen"]} for row in EXECUTION_FIELDS],
        "gaps": sorted(set(gaps)),
        "required_resolution": "superseding_freeze_review",
        "scientific_campaign_started": False,
    }


def build_execution_package_preview(
    campaign: dict[str, Any], official_freeze: dict[str, Any], contract_dir: Path = CONTRACT_DIR
) -> dict[str, Any]:
    readiness = audit_execution_readiness(campaign, official_freeze)
    contracts = _contract_payloads(contract_dir)
    contract_digests = {name: digest(value) for name, value in sorted(contracts.items())}
    identity = {
        "schema_version": EXECUTION_PACKAGE_SCHEMA,
        "official_freeze_id": official_freeze["freeze_id"],
        "official_freeze_digest": official_freeze["canonical_payload_sha256"],
        "contract_digests": contract_digests,
        "status": readiness["status"],
        "blockers": readiness["gaps"],
    }
    return {
        **identity,
        "canonical_digest": digest(identity),
        "candidate_created": False,
        "official_execution_package": False,
        "execution_package_commit_sha": "unresolved_until_commit",
        "scenario_templates": readiness["scenario_templates"],
        "execution_sessions": 0,
        "run_plan_materialized": False,
        "execution_allowed": False,
        "scientific_campaign_started": False,
    }


def validate_execution_package_preview(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "official_freeze_id", "official_freeze_digest", "contract_digests",
        "status", "blockers", "canonical_digest", "candidate_created", "official_execution_package",
        "execution_package_commit_sha", "scenario_templates", "execution_sessions",
        "run_plan_materialized", "execution_allowed", "scientific_campaign_started",
    }
    if set(value) != required or value["schema_version"] != EXECUTION_PACKAGE_SCHEMA:
        raise ContractError("invalid execution package preview fields")
    identity = {key: value[key] for key in (
        "schema_version", "official_freeze_id", "official_freeze_digest", "contract_digests", "status", "blockers"
    )}
    if value["canonical_digest"] != digest(identity):
        raise ContractError("execution package preview integrity mismatch")
    if value["status"] == BLOCKED_STATUS:
        forbidden_truths = ("candidate_created", "official_execution_package", "run_plan_materialized", "execution_allowed", "scientific_campaign_started")
        if any(value[name] for name in forbidden_truths) or value["execution_sessions"] != 0:
            raise ContractError("blocked preview cannot authorize or describe execution")
    return value


def inspect_run_plan(campaign: dict[str, Any], official_freeze: dict[str, Any]) -> dict[str, Any]:
    readiness = audit_execution_readiness(campaign, official_freeze)
    return {
        "status": readiness["status"],
        "run_plan_materialized": False,
        "scenario_templates": readiness["scenario_templates"],
        "execution_sessions": 0,
        "repetition_policy": "not_frozen",
        "ordering_policy": "not_frozen",
        "concurrency_policy": "not_frozen",
        "split_materialization": "blocked",
        "blockers": readiness["gaps"],
        "execution_allowed": False,
    }


def inspect_label_boundary(contract_dir: Path = CONTRACT_DIR) -> dict[str, Any]:
    value = _contract_payloads(contract_dir)["label_vault"]
    if value.get("initial_state") != "absent_locked" or value.get("labels_created") is not False:
        raise ContractError("label vault contract must start empty and locked")
    forbidden = set(value["evaluator_boundary"]["forbidden_fields"])
    required = {"behavior_type", "generator_family", "scenario_token", "session_token", "seed", "split_assignment"}
    if not required <= forbidden:
        raise ContractError("evaluator metadata guard is incomplete")
    return {
        "valid": True,
        "label_vault_status": value["initial_state"],
        "labels_created": False,
        "labels_unlocked": False,
        "runner_evaluator_separated": True,
        "forbidden_metadata_guard_passed": True,
        "forbidden_evaluator_fields": sorted(forbidden),
    }
