from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .contracts import ContractError, digest, load_json, write_canonical
from .operational_initialization import (
    INITIALIZATION_CONTRACT_PATH,
    LEDGER_CONTRACT_PATH,
    MAPPING_CONTRACT_PATH,
    audit_initialization_contracts,
)
from .phase1_execution_package import (
    OFFICIAL_PACKAGE_PATH as PREDECESSOR_PACKAGE_PATH,
    RUN_PLAN_PATH,
    validate_official_package as validate_predecessor_package,
    validate_run_plan,
)
from .superseding_freeze import validate_official as validate_superseding_freeze


ROOT = Path(__file__).resolve().parents[2]
EXECUTION = Path(__file__).with_name("execution")
SUPERSEDING_FREEZE_PATH = Path(__file__).with_name("freeze") / "official_superseding_freeze.json"
OFFICIAL_PACKAGE_V2_PATH = EXECUTION / "official_execution_package_v2.json"

PACKAGE_SCHEMA = "network_validation_official_superseding_execution_package_v2"
PACKAGE_GENERATION = "superseding_operational_v2"
SUPERSEDING_REASON = "operational_initialization_contract_completion"
PREDECESSOR_PACKAGE_ID = "network-validation-execution-2ae1f6567e7eb4f8"
PREDECESSOR_PACKAGE_DIGEST = "2ae1f6567e7eb4f8d4829e1ae1210e478763863271b323b16d34095105522492"
SCIENTIFIC_INPUTS_COMMIT = "903cb3db7e0303892c2436e32f44b1c4a64e1034"
HEX40 = re.compile(r"^[0-9a-f]{40}$")

SCIENTIFIC_DIGEST_FIELDS = (
    "superseding_freeze_digest",
    "campaign_digest",
    "run_plan_digest",
    "run_plan_manifest_digest",
    "exact_execution_order_digest",
    "split_assignments_digest",
    "image_lock_digest",
    "feature_contract_digest",
    "feature_order_digest",
    "acceptance_criteria_digest",
    "counterfactual_digest",
    "execution_policy_digest",
    "compose_runtime_digest",
    "runner_contract_digest",
    "evaluator_contract_digest",
    "label_vault_contract_digest",
    "output_contract_digest",
    "preflight_contract_digest",
    "session_integrity_contract_digest",
)

OPERATIONAL_SOURCE_PATHS = (
    MAPPING_CONTRACT_PATH,
    LEDGER_CONTRACT_PATH,
    INITIALIZATION_CONTRACT_PATH,
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _git_commit_exists(sha: str) -> bool:
    return _git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def _commit_contains_current_file(sha: str, path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"{sha}:{relative}"], cwd=ROOT, capture_output=True, check=False
    )
    return result.returncode == 0 and result.stdout == path.read_bytes()


def validate_operational_contracts_commit(sha: str) -> None:
    if not HEX40.fullmatch(sha) or not _git_commit_exists(sha):
        raise ContractError("operational contracts commit is invalid")
    if not all(_commit_contains_current_file(sha, path) for path in OPERATIONAL_SOURCE_PATHS):
        raise ContractError("operational contracts commit does not contain current contracts")


def scientific_equivalence() -> dict[str, Any]:
    predecessor = validate_predecessor_package()
    freeze = validate_superseding_freeze(load_json(SUPERSEDING_FREEZE_PATH))
    run_plan = validate_run_plan(load_json(RUN_PLAN_PATH))
    units = load_json(RUN_PLAN_PATH)["ordered_execution_units"]
    comparisons = {field: predecessor[field] for field in SCIENTIFIC_DIGEST_FIELDS}
    if predecessor["package_id"] != PREDECESSOR_PACKAGE_ID or predecessor["canonical_payload_sha256"] != PREDECESSOR_PACKAGE_DIGEST:
        raise ContractError("predecessor package identity mismatch")
    if freeze["canonical_payload_sha256"] != predecessor["superseding_freeze_digest"]:
        raise ContractError("superseding freeze drift")
    if run_plan["run_plan_digest"] != predecessor["run_plan_digest"]:
        raise ContractError("run plan drift")
    if run_plan["exact_execution_order_digest"] != predecessor["exact_execution_order_digest"]:
        raise ContractError("exact execution order drift")
    if len(units) != 864 or len({row["execution_token"] for row in units}) != 864:
        raise ContractError("execution unit identity drift")
    if len({(row["scenario_token"], row["repetition_index"], row["execution_seed"]) for row in units}) != 864:
        raise ContractError("scientific seed identity drift")
    if freeze["scenario_template_count"] != 288 or freeze["repetitions_per_template"] != 3:
        raise ContractError("scenario or repetition drift")
    if freeze["proxy_validation"] != {"passed": True, "warning_count": 0, "warnings": []}:
        raise ContractError("proxy warning drift")
    nuisance = freeze["nuisance_factor_validation"]
    if nuisance["infrastructure_to_port_lock"] or nuisance["infrastructure_to_target_lock"] or nuisance["target_to_port_lock"]:
        raise ContractError("nuisance lock drift")
    campaign = load_json(Path(__file__).with_name("config") / "superseding_freeze_campaign.json")
    if len(campaign["counterfactual_pairs"]) != 24:
        raise ContractError("counterfactual pair drift")
    return {
        "valid": True,
        "scenario_templates": 288,
        "execution_sessions": 864,
        "execution_tokens_unchanged": True,
        "scientific_seeds_unchanged": True,
        "counterfactual_pairs": 24,
        "proxy_warning_count": 0,
        "nuisance_warning_count": 0,
        "digests": comparisons,
    }


def _identity(value: dict[str, Any]) -> dict[str, Any]:
    excluded = {"package_id", "canonical_digest", "created_at"}
    return {key: item for key, item in value.items() if key not in excluded}


def build_payload(operational_contracts_commit_sha: str, created_at: str) -> dict[str, Any]:
    predecessor = validate_predecessor_package()
    equivalence = scientific_equivalence()
    contracts = audit_initialization_contracts()
    value: dict[str, Any] = {
        "schema_version": PACKAGE_SCHEMA,
        "package_type": "phase1_data_collection",
        "package_generation": PACKAGE_GENERATION,
        "supersedes_package_id": predecessor["package_id"],
        "supersedes_package_digest": predecessor["canonical_payload_sha256"],
        "superseding_reason": SUPERSEDING_REASON,
        "scientific_inputs_commit_sha": SCIENTIFIC_INPUTS_COMMIT,
        "operational_contracts_commit_sha": operational_contracts_commit_sha,
        "superseding_freeze_id": predecessor["superseding_freeze_id"],
        "superseding_freeze_digest": predecessor["superseding_freeze_digest"],
        "superseding_freeze_commit_sha": predecessor["superseding_freeze_commit_sha"],
        "campaign_digest": predecessor["campaign_digest"],
        "run_plan_digest": predecessor["run_plan_digest"],
        "run_plan_manifest_digest": predecessor["run_plan_manifest_digest"],
        "exact_execution_order_digest": predecessor["exact_execution_order_digest"],
        "exact_order_digest": predecessor["exact_execution_order_digest"],
        "split_assignments_digest": predecessor["split_assignments_digest"],
        "split_digest": predecessor["split_assignments_digest"],
        "image_lock_digest": predecessor["image_lock_digest"],
        "feature_contract_digest": predecessor["feature_contract_digest"],
        "feature_order_digest": predecessor["feature_order_digest"],
        "acceptance_criteria_digest": predecessor["acceptance_criteria_digest"],
        "counterfactual_digest": predecessor["counterfactual_digest"],
        "execution_policy_digest": predecessor["execution_policy_digest"],
        "compose_runtime_digest": predecessor["compose_runtime_digest"],
        "runner_contract_digest": predecessor["runner_contract_digest"],
        "evaluator_contract_digest": predecessor["evaluator_contract_digest"],
        "label_vault_contract_digest": predecessor["label_vault_contract_digest"],
        "output_contract_digest": predecessor["output_contract_digest"],
        "preflight_contract_digest": predecessor["preflight_contract_digest"],
        "session_integrity_contract_digest": predecessor["session_integrity_contract_digest"],
        "sealed_mapping_contract_digest": contracts["sealed_mapping_contract_digest"],
        "ledger_contract_digest": contracts["ledger_contract_digest"],
        "initialization_contract_digest": contracts["initialization_contract_digest"],
        "scenario_template_count": equivalence["scenario_templates"],
        "repetitions_per_template": 3,
        "execution_session_count": equivalence["execution_sessions"],
        "counterfactual_pair_count": equivalence["counterfactual_pairs"],
        "proxy_warning_count": equivalence["proxy_warning_count"],
        "nuisance_warning_count": equivalence["nuisance_warning_count"],
        "scientific_protocol_changed": False,
        "scientific_run_plan_changed": False,
        "scientific_split_changed": False,
        "scientific_seed_policy_changed": False,
        "scientific_image_identity_changed": False,
        "scientific_feature_contract_changed": False,
        "scientific_acceptance_criteria_changed": False,
        "operational_initialization_contract_complete": True,
        "runtime_preflight_required": True,
        "campaign_initialization_required": True,
        "scientific_campaign_started": False,
        "scientific_sessions_executed": 0,
        "created_at": created_at,
    }
    canonical = digest(_identity(value))
    value["package_id"] = f"network-validation-execution-{canonical[:16]}"
    value["canonical_digest"] = canonical
    return value


def validate_package(value: dict[str, Any]) -> dict[str, Any]:
    operational_sha = value.get("operational_contracts_commit_sha", "")
    validate_operational_contracts_commit(operational_sha)
    expected = build_payload(operational_sha, value.get("created_at", ""))
    if value != expected:
        raise ContractError("superseding execution package integrity mismatch")
    if value["canonical_digest"] != digest(_identity(value)):
        raise ContractError("superseding execution package canonical digest mismatch")
    if not value["package_id"].endswith(value["canonical_digest"][:16]):
        raise ContractError("superseding execution package ID mismatch")
    if value["package_id"] == PREDECESSOR_PACKAGE_ID:
        raise ContractError("superseding execution package reused predecessor ID")
    return value


def build_preview(operational_contracts_commit_sha: str) -> dict[str, Any]:
    value = build_payload(operational_contracts_commit_sha, "operational_audit_timestamp_excluded_from_identity")
    return {
        "official_superseding_execution_package_created": False,
        "official_superseding_execution_package_valid": False,
        "scientific_equivalence_valid": scientific_equivalence()["valid"],
        "operational_initialization_contract_complete": True,
        "candidate": value,
    }


def write_official_package(path: Path, operational_contracts_commit_sha: str, created_at: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise ContractError("official superseding execution package requires explicit confirmation")
    if path.exists():
        raise ContractError("official superseding execution package cannot be overwritten")
    validate_operational_contracts_commit(operational_contracts_commit_sha)
    value = build_payload(operational_contracts_commit_sha, created_at)
    validate_package(value)
    write_canonical(path, value)
    return value


def validate_official_package(path: Path = OFFICIAL_PACKAGE_V2_PATH) -> dict[str, Any]:
    return validate_package(load_json(path))
