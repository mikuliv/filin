from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from .causal_guard import feature_order
from .contracts import ContractError, digest, load_json, write_canonical
from .phase1_runtime import (
    RUNTIME_CONTRACT_PATH,
    runtime_contract_digest,
    validate_runtime_contract,
)
from .superseding_execution_package import SCIENTIFIC_DIGEST_FIELDS
from .superseding_freeze import validate_inputs

ROOT = Path(__file__).resolve().parents[2]
EXECUTION = Path(__file__).with_name("execution")
PREDECESSOR_PACKAGE_PATH = EXECUTION / "official_execution_package_v4.json"
OFFICIAL_RUNTIME_PACKAGE_V5_PATH = EXECUTION / "official_execution_package_v5.json"
RUNTIME_SUPPORT_PATH = Path(__file__).with_name("phase1_runtime.py")
DOCKER_RUNNER_PATH = Path(__file__).with_name("phase1_docker_runner.py")
PACKAGE_BUILDER_PATH = Path(__file__)
CLI_PATH = Path(__file__).with_name("cli.py")
CONFIG = Path(__file__).with_name("config")
FREEZE = Path(__file__).with_name("freeze")
CAMPAIGN_PATH = CONFIG / "superseding_freeze_campaign.json"
POLICY_PATH = CONFIG / "superseding_execution_policy.json"
SPLIT_PATH = CONFIG / "superseding_split_assignments.json"
IMAGE_PATH = CONFIG / "superseding_image_lock.json"
ACCEPTANCE_CRITERIA_PATH = CONFIG / "acceptance_criteria.json"
SUPERSEDING_FREEZE_PATH = FREEZE / "official_superseding_freeze.json"
RUN_PLAN_PATH = EXECUTION / "phase1_run_plan.json"
COMPOSE_PATH = Path(__file__).with_name("compose.yaml")
FEATURE_CONTRACT_PATH = ROOT / "ml/experiments/v0_3_15_4/feature_contract_v2.yaml"

PACKAGE_SCHEMA = "network_validation_official_runtime_execution_package_v5"
PACKAGE_GENERATION = "superseding_operational_runtime_v5"
SUPERSEDING_REASON = "zeek_absolute_path_and_non_login_shell"
PREDECESSOR_PACKAGE_ID = "network-validation-execution-8e1e32b127893bdf"
PREDECESSOR_PACKAGE_DIGEST = "8e1e32b127893bdf2e32114b7fb2db19e0e06b2b3de1df5ce2308d2e5571e6cf"
ZEEK_EXECUTABLE = "/usr/local/zeek/bin/zeek"
ZEEK_SHELL_MODE = "bash -c"
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


def _canonical_source_bytes(path: Path) -> bytes:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in content:
        raise ContractError(f"runtime source contains unsupported line ending: {path.name}")
    return content


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(_canonical_source_bytes(path)).hexdigest()


def _commit_contains_current_file(sha: str, path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(["git", "show", f"{sha}:{relative}"], cwd=ROOT, capture_output=True, check=False)
    return result.returncode == 0 and result.stdout == _canonical_source_bytes(path)


def validate_runtime_sources_commit(sha: str) -> None:
    if not HEX40.fullmatch(sha) or _git("cat-file", "-e", f"{sha}^{{commit}}").returncode:
        raise ContractError("runtime v5 sources commit is invalid")
    if not all(_commit_contains_current_file(sha, path) for path in RUNTIME_SOURCE_PATHS):
        raise ContractError("runtime v5 sources commit does not contain current runtime sources")


def _identity(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"package_id", "canonical_digest", "created_at"}}


def validate_predecessor_package() -> dict[str, Any]:
    value = load_json(PREDECESSOR_PACKAGE_PATH)
    if value.get("package_id") != PREDECESSOR_PACKAGE_ID or value.get("canonical_digest") != PREDECESSOR_PACKAGE_DIGEST:
        raise ContractError("runtime v4 predecessor identity mismatch")
    if value["canonical_digest"] != digest(_identity(value)):
        raise ContractError("runtime v4 predecessor canonical digest mismatch")
    source = value.get("runtime_sources_commit_sha", "")
    if not HEX40.fullmatch(source) or _git("cat-file", "-e", f"{source}^{{commit}}").returncode:
        raise ContractError("runtime v4 source commit is unavailable")
    historical_paths = {
        "phase1_runtime_contract_digest": "lab/network_validation/execution/phase1_runtime_contract.json",
        "phase1_runtime_support_sha256": "lab/network_validation/phase1_runtime.py",
        "phase1_docker_runner_sha256": "lab/network_validation/phase1_docker_runner.py",
        "runtime_package_builder_sha256": "lab/network_validation/runtime_execution_package_v4.py",
        "phase1_cli_sha256": "lab/network_validation/cli.py",
    }
    for field, relative in historical_paths.items():
        result = subprocess.run(["git", "show", f"{source}:{relative}"], cwd=ROOT, capture_output=True, check=False)
        if result.returncode:
            raise ContractError(f"runtime v4 source missing: {relative}")
        if field == "phase1_runtime_contract_digest":
            observed = digest(json.loads(result.stdout.decode("utf-8")))
        else:
            observed = hashlib.sha256(result.stdout).hexdigest()
        if observed != value[field]:
            raise ContractError(f"runtime v4 source digest mismatch: {field}")
    return value


def validate_corrected_zeek_runner() -> None:
    source = _canonical_source_bytes(DOCKER_RUNNER_PATH).decode("utf-8")
    start = source.index("    def _run_zeek(")
    end = source.index("    def _prepare_model_input_zeek(", start)
    relevant = source[start:end]
    if ZEEK_EXECUTABLE not in relevant:
        raise ContractError("corrected Zeek executable is absent")
    if '"-c", command' not in relevant or '"-lc"' in relevant or "bash -lc" in relevant:
        raise ContractError("corrected Zeek shell mode is absent")


def _contract_digest(name: str) -> str:
    return digest(load_json(EXECUTION / name))


def _validate_current_run_plan() -> dict[str, Any]:
    assignments = load_json(SPLIT_PATH)
    units = assignments["ordered_execution_units"]
    value = {
        "schema_version": "network_validation_phase1_run_plan_v1",
        "campaign_digest": load_json(CAMPAIGN_PATH)["canonical_digest"],
        "execution_policy_digest": load_json(POLICY_PATH)["canonical_digest"],
        "compose_runtime_digest": hashlib.sha256(_canonical_source_bytes(COMPOSE_PATH)).hexdigest(),
        "split_assignments_digest": assignments["canonical_digest"],
        "scenario_template_count": 288,
        "repetitions_per_template": 3,
        "execution_session_count": 864,
        "run_plan_digest": digest(units),
        "exact_execution_order_digest": digest([row["execution_token"] for row in units]),
        "ordered_execution_units": units,
    }
    value["canonical_digest"] = digest(value)
    actual = load_json(RUN_PLAN_PATH)
    if actual != value:
        raise ContractError("current Phase 1 run plan is not canonical")
    return actual


def scientific_equivalence_to_v4(predecessor: dict[str, Any] | None = None) -> dict[str, Any]:
    predecessor = predecessor or validate_predecessor_package()
    inputs = validate_inputs()
    plan = _validate_current_run_plan()
    campaign = load_json(CAMPAIGN_PATH)
    freeze = load_json(SUPERSEDING_FREEZE_PATH)
    criteria = load_json(ACCEPTANCE_CRITERIA_PATH)
    order = feature_order()
    backgrounds = Counter(row["background_policy"] for row in campaign["scenario_templates"])
    if backgrounds != Counter({"http": 72, "dns": 72, "keepalive": 72, "combined": 72}):
        raise ContractError("background policy distribution drift")
    observed = {
        "superseding_freeze_digest": freeze["canonical_payload_sha256"],
        "campaign_digest": inputs["campaign_digest"],
        "run_plan_digest": plan["run_plan_digest"],
        "run_plan_manifest_digest": plan["canonical_digest"],
        "exact_execution_order_digest": plan["exact_execution_order_digest"],
        "split_assignments_digest": inputs["split_assignment_digest"],
        "image_lock_digest": inputs["image_lock_digest"],
        "feature_contract_digest": hashlib.sha256(_canonical_source_bytes(FEATURE_CONTRACT_PATH)).hexdigest(),
        "feature_order_digest": digest(order),
        "acceptance_criteria_digest": criteria["canonical_digest"],
        "counterfactual_digest": digest(campaign["counterfactual_pairs"]),
        "execution_policy_digest": inputs["execution_policy_digest"],
        "compose_runtime_digest": hashlib.sha256(_canonical_source_bytes(COMPOSE_PATH)).hexdigest(),
        "runner_contract_digest": _contract_digest("runner_contract.json"),
        "evaluator_contract_digest": _contract_digest("evaluator_contract.json"),
        "label_vault_contract_digest": _contract_digest("label_vault_contract.json"),
        "output_contract_digest": _contract_digest("output_contract.json"),
        "preflight_contract_digest": _contract_digest("phase1_preflight_contract.json"),
        "session_integrity_contract_digest": _contract_digest("session_integrity_contract.json"),
    }
    for field in SCIENTIFIC_DIGEST_FIELDS:
        if observed[field] != predecessor[field]:
            raise ContractError(f"scientific input drift from v4: {field}")
    if len(order) != 51:
        raise ContractError("feature order cardinality drift")
    return {
        "valid": True,
        "scenario_templates": inputs["scenario_templates"],
        "execution_sessions": inputs["execution_sessions"],
        "counterfactual_pairs": inputs["counterfactual_pair_count"],
        "features": len(order),
        "split_counts": inputs["split_counts"],
        "background_counts": dict(sorted(backgrounds.items())),
        "proxy_warning_count": inputs["proxy_warning_count"],
        "nuisance_warning_count": inputs["nuisance_factor_warning_count"],
        "digests": observed,
    }


def build_payload(runtime_sources_commit_sha: str, created_at: str) -> dict[str, Any]:
    validate_runtime_sources_commit(runtime_sources_commit_sha)
    predecessor = validate_predecessor_package()
    equivalence = scientific_equivalence_to_v4(predecessor)
    validate_runtime_contract()
    validate_corrected_zeek_runner()
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
        "zeek_executable": ZEEK_EXECUTABLE,
        "zeek_shell_mode": ZEEK_SHELL_MODE,
        "zeek_login_shell_used": False,
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
        "secret_acl_allowlist_enforced": True,
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
        predecessor = validate_predecessor_package()
        return {
            "official_runtime_execution_package_created": False,
            "official_runtime_execution_package_valid": False,
            "candidate_identity": {
                "runtime_sources_commit_sha": "unresolved_until_commit",
                "supersedes_package_id": predecessor["package_id"],
                "supersedes_package_digest": predecessor["canonical_digest"],
                "phase1_runtime_contract_digest": runtime_contract_digest(),
                "phase1_runtime_support_sha256": _sha256_file(RUNTIME_SUPPORT_PATH),
                "phase1_docker_runner_sha256": _sha256_file(DOCKER_RUNNER_PATH),
                "runtime_package_builder_sha256": _sha256_file(PACKAGE_BUILDER_PATH),
                "phase1_cli_sha256": _sha256_file(CLI_PATH),
                "zeek_executable": ZEEK_EXECUTABLE,
                "zeek_shell_mode": ZEEK_SHELL_MODE,
                "scientific_equivalence_valid": scientific_equivalence_to_v4(predecessor)["valid"],
            },
            "blockers": [
                "runtime_v5_sources_not_committed",
                "official_runtime_execution_package_v5_not_created",
                "fresh_campaign_initialization_required",
            ],
        }
    value = build_payload(runtime_sources_commit_sha, "operational_audit_timestamp_excluded_from_identity")
    return {
        "official_runtime_execution_package_created": False,
        "official_runtime_execution_package_valid": False,
        "scientific_equivalence_valid": True,
        "candidate": value,
        "blockers": ["official_runtime_execution_package_v5_not_created", "fresh_campaign_initialization_required"],
    }


def validate_package(value: dict[str, Any]) -> dict[str, Any]:
    source = value.get("runtime_sources_commit_sha", "")
    expected = build_payload(source, value.get("created_at", ""))
    if value != expected:
        raise ContractError("runtime v5 execution package integrity mismatch")
    if value["canonical_digest"] != digest(_identity(value)):
        raise ContractError("runtime v5 execution package canonical digest mismatch")
    if value["package_id"] == value["supersedes_package_id"]:
        raise ContractError("runtime v5 execution package reused predecessor ID")
    return value


def write_official_package(path: Path, runtime_sources_commit_sha: str, created_at: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise ContractError("official runtime v5 execution package requires explicit confirmation")
    if path.exists():
        raise ContractError("official runtime v5 execution package cannot be overwritten")
    value = build_payload(runtime_sources_commit_sha, created_at)
    validate_package(value)
    write_canonical(path, value)
    return value


def validate_official_package(path: Path = OFFICIAL_RUNTIME_PACKAGE_V5_PATH) -> dict[str, Any]:
    return validate_package(load_json(path))
