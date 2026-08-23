from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from .contracts import ContractError, digest, load_json, write_canonical
from .phase1_runtime import (
    RUNTIME_CONTRACT_PATH,
    runtime_contract_digest,
    validate_runtime_contract,
)
from .superseding_execution_package import (
    OFFICIAL_PACKAGE_V2_PATH,
    SCIENTIFIC_DIGEST_FIELDS,
    scientific_equivalence,
)
from .superseding_execution_package import (
    validate_official_package as validate_predecessor_package,
)

ROOT = Path(__file__).resolve().parents[2]
EXECUTION = Path(__file__).with_name("execution")
OFFICIAL_RUNTIME_PACKAGE_PATH = EXECUTION / "official_execution_package_v3.json"
RUNTIME_SUPPORT_PATH = Path(__file__).with_name("phase1_runtime.py")
DOCKER_RUNNER_PATH = Path(__file__).with_name("phase1_docker_runner.py")
PACKAGE_BUILDER_PATH = Path(__file__)
CLI_PATH = Path(__file__).with_name("cli.py")

PACKAGE_SCHEMA = "network_validation_official_runtime_execution_package_v3"
PACKAGE_GENERATION = "superseding_operational_runtime_v3"
SUPERSEDING_REASON = "phase1_runtime_contract_completion"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
RUNTIME_SOURCE_PATHS = (
    RUNTIME_CONTRACT_PATH,
    RUNTIME_SUPPORT_PATH,
    DOCKER_RUNNER_PATH,
    PACKAGE_BUILDER_PATH,
    CLI_PATH,
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _sha256_file(path: Path) -> str:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in content:
        raise ContractError(f"runtime source contains unsupported line ending: {path.name}")
    return hashlib.sha256(content).hexdigest()


def _commit_contains_current_file(sha: str, path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"{sha}:{relative}"], cwd=ROOT, capture_output=True, check=False
    )
    current = path.read_bytes().replace(b"\r\n", b"\n")
    return result.returncode == 0 and result.stdout == current


def validate_runtime_sources_commit(sha: str) -> None:
    if not HEX40.fullmatch(sha) or _git("cat-file", "-e", f"{sha}^{{commit}}").returncode:
        raise ContractError("runtime sources commit is invalid")
    if not all(_commit_contains_current_file(sha, path) for path in RUNTIME_SOURCE_PATHS):
        raise ContractError("runtime sources commit does not contain current runtime sources")


def _identity(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"package_id", "canonical_digest", "created_at"}}


def build_payload(runtime_sources_commit_sha: str, created_at: str) -> dict[str, Any]:
    validate_runtime_sources_commit(runtime_sources_commit_sha)
    predecessor = validate_predecessor_package(OFFICIAL_PACKAGE_V2_PATH)
    equivalence = scientific_equivalence()
    validate_runtime_contract()
    value: dict[str, Any] = {
        "schema_version": PACKAGE_SCHEMA,
        "package_type": "phase1_data_collection",
        "package_generation": PACKAGE_GENERATION,
        "supersedes_package_id": predecessor["package_id"],
        "supersedes_package_digest": predecessor["canonical_digest"],
        "superseding_reason": SUPERSEDING_REASON,
        "scientific_inputs_commit_sha": predecessor["scientific_inputs_commit_sha"],
        "operational_contracts_commit_sha": predecessor["operational_contracts_commit_sha"],
        "runtime_sources_commit_sha": runtime_sources_commit_sha,
        "superseding_freeze_id": predecessor["superseding_freeze_id"],
        "sealed_mapping_contract_digest": predecessor["sealed_mapping_contract_digest"],
        "ledger_contract_digest": predecessor["ledger_contract_digest"],
        "initialization_contract_digest": predecessor["initialization_contract_digest"],
        "phase1_runtime_contract_digest": runtime_contract_digest(),
        "phase1_runtime_support_sha256": _sha256_file(RUNTIME_SUPPORT_PATH),
        "phase1_docker_runner_sha256": _sha256_file(DOCKER_RUNNER_PATH),
        "runtime_package_builder_sha256": _sha256_file(PACKAGE_BUILDER_PATH),
        "phase1_cli_sha256": _sha256_file(CLI_PATH),
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
        "operational_runtime_contract_complete": True,
        "canonical_phase1_runner_available": True,
        "fresh_campaign_initialization_required": True,
        "predecessor_initialization_reuse_allowed": False,
        "runtime_preflight_required": True,
        "per_session_preflight_required": True,
        "scientific_session_execution_allowed_after_per_session_preflight": True,
        "maximum_completed_units_per_runner_invocation": 1,
        "scientific_campaign_started": False,
        "scientific_sessions_executed": 0,
        "created_at": created_at,
    }
    for field in SCIENTIFIC_DIGEST_FIELDS:
        value[field] = predecessor[field]
    canonical = digest(_identity(value))
    value["package_id"] = f"network-validation-execution-{canonical[:16]}"
    value["canonical_digest"] = canonical
    return value


def build_preview(runtime_sources_commit_sha: str | None = None) -> dict[str, Any]:
    if runtime_sources_commit_sha is None:
        source = "unresolved_until_commit"
        predecessor = validate_predecessor_package(OFFICIAL_PACKAGE_V2_PATH)
        value: dict[str, Any] = {
            "runtime_sources_commit_sha": source,
            "supersedes_package_id": predecessor["package_id"],
            "supersedes_package_digest": predecessor["canonical_digest"],
            "phase1_runtime_contract_digest": runtime_contract_digest(),
            "phase1_runtime_support_sha256": _sha256_file(RUNTIME_SUPPORT_PATH),
            "phase1_docker_runner_sha256": _sha256_file(DOCKER_RUNNER_PATH),
            "runtime_package_builder_sha256": _sha256_file(PACKAGE_BUILDER_PATH),
            "phase1_cli_sha256": _sha256_file(CLI_PATH),
            "scientific_equivalence_valid": scientific_equivalence()["valid"],
            "operational_runtime_contract_complete": True,
        }
        return {
            "official_runtime_execution_package_created": False,
            "official_runtime_execution_package_valid": False,
            "candidate_identity": value,
            "blockers": ["runtime_sources_not_committed", "official_runtime_execution_package_not_created", "fresh_campaign_initialization_required"],
        }
    value = build_payload(runtime_sources_commit_sha, "operational_audit_timestamp_excluded_from_identity")
    return {
        "official_runtime_execution_package_created": False,
        "official_runtime_execution_package_valid": False,
        "candidate": value,
        "blockers": ["official_runtime_execution_package_not_created", "fresh_campaign_initialization_required"],
    }


def validate_package(value: dict[str, Any]) -> dict[str, Any]:
    source = value.get("runtime_sources_commit_sha", "")
    expected = build_payload(source, value.get("created_at", ""))
    if value != expected:
        raise ContractError("runtime execution package integrity mismatch")
    if value["canonical_digest"] != digest(_identity(value)):
        raise ContractError("runtime execution package canonical digest mismatch")
    if value["package_id"] == value["supersedes_package_id"]:
        raise ContractError("runtime execution package reused predecessor ID")
    return value


def write_official_package(path: Path, runtime_sources_commit_sha: str, created_at: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise ContractError("official runtime execution package requires explicit confirmation")
    if path.exists():
        raise ContractError("official runtime execution package cannot be overwritten")
    value = build_payload(runtime_sources_commit_sha, created_at)
    validate_package(value)
    write_canonical(path, value)
    return value


def validate_official_package(path: Path = OFFICIAL_RUNTIME_PACKAGE_PATH) -> dict[str, Any]:
    return validate_package(load_json(path))
