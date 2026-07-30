from __future__ import annotations

import hashlib
import importlib.metadata
import locale
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from .causal_guard import feature_order
from .contracts import ENVIRONMENT_SCHEMA, FREEZE_SCHEMA, ContractError, digest, validate_campaign


def _command(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
        if result.returncode:
            return "unavailable"
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def validate_environment_lock(value: dict[str, Any]) -> None:
    required = {
        "schema_version", "os", "architecture", "python_version",
        "pip_dependency_lock_digest", "scikit_learn_version", "joblib_version",
        "docker_version", "docker_compose_version", "zeek_image_name",
        "zeek_image_digest", "client_image_digest", "target_image_digests",
        "source_git_commit", "dirty_working_tree", "feature_contract_digest",
        "feature_order_digest", "timezone", "locale", "canonical_digest",
    }
    if set(value) != required:
        raise ContractError("environment lock fields mismatch")
    if value["schema_version"] != ENVIRONMENT_SCHEMA:
        raise ContractError("environment lock schema mismatch")
    if not isinstance(value["dirty_working_tree"], bool):
        raise ContractError("dirty working tree flag must be boolean")
    without_digest = {key: item for key, item in value.items() if key != "canonical_digest"}
    if value["canonical_digest"] != digest(without_digest):
        raise ContractError("environment lock digest mismatch")


def environment_lock(root: Path, images: dict[str, str]) -> dict[str, Any]:
    order = feature_order()
    pip_lock = root / "lab/network_validation/requirements.lock"
    lock = {
        "schema_version": ENVIRONMENT_SCHEMA,
        "os": platform.system(), "architecture": platform.machine(), "python_version": platform.python_version(),
        "pip_dependency_lock_digest": hashlib.sha256(pip_lock.read_bytes()).hexdigest(),
        "scikit_learn_version": importlib.metadata.version("scikit-learn"),
        "joblib_version": importlib.metadata.version("joblib"),
        "docker_version": _command(["docker", "version", "--format", "{{.Client.Version}}"]),
        "docker_compose_version": _command(["docker", "compose", "version", "--short"]),
        "zeek_image_name": "zeek/zeek:7.0.5", "zeek_image_digest": images.get("zeek", "unresolved"),
        "client_image_digest": images.get("client", "unresolved"), "target_image_digests": images.get("targets", {}),
        "source_git_commit": _command(["git", "-C", str(root), "rev-parse", "HEAD"]),
        "dirty_working_tree": bool(_command(["git", "-C", str(root), "status", "--porcelain"])),
        "feature_contract_digest": hashlib.sha256((root / "ml/experiments/v0_3_15_4/feature_contract_v2.yaml").read_bytes()).hexdigest(),
        "feature_order_digest": digest(order), "timezone": os.environ.get("TZ", "system_default"),
        "locale": locale.getlocale()[0] or "system_default",
    }
    lock["canonical_digest"] = digest(lock)
    validate_environment_lock(lock)
    return lock


def freeze_preview(campaign: dict[str, Any], environment: dict[str, Any], compose_digest: str, source_commit: str) -> dict[str, Any]:
    validate_campaign(campaign)
    from .planning import proxy_risks, validate_counterfactuals, validate_infrastructure_profiles, validate_split
    validate_infrastructure_profiles(campaign["infrastructure_profiles"])
    validate_counterfactuals(campaign)
    validate_split(campaign["split_policy"]["fixture_assignments"], campaign["split_policy"])
    validate_environment_lock(environment)
    order = feature_order()
    if environment["feature_order_digest"] != digest(order):
        raise ContractError("environment feature order mismatch")
    if environment["feature_contract_digest"] != hashlib.sha256(Path(__file__).resolve().parents[2].joinpath("ml/experiments/v0_3_15_4/feature_contract_v2.yaml").read_bytes()).hexdigest():
        raise ContractError("environment feature contract mismatch")
    if not isinstance(compose_digest, str) or len(compose_digest) != 64 or any(character not in "0123456789abcdef" for character in compose_digest):
        raise ContractError("invalid Compose configuration digest")
    if not isinstance(source_commit, str) or len(source_commit) != 40 or any(character not in "0123456789abcdef" for character in source_commit):
        raise ContractError("invalid source commit")
    criteria = campaign["acceptance_criteria"]
    unresolved = sorted(key for key, value in criteria.items() if value == "TBD_BEFORE_FREEZE")
    unresolved_integrity = []
    if environment.get("client_image_digest") == "unresolved":
        unresolved_integrity.append("client_image_digest")
    if environment.get("zeek_image_digest") == "unresolved":
        unresolved_integrity.append("zeek_image_digest")
    targets = environment.get("target_image_digests")
    if not isinstance(targets, dict) or set(targets) != {"target_a", "target_b"} or any(value == "unresolved" for value in targets.values()):
        unresolved_integrity.append("target_image_digests")
    if environment.get("dirty_working_tree"):
        unresolved_integrity.append("dirty_working_tree")
    risks = proxy_risks(campaign)
    if risks:
        unresolved_integrity.append("proxy_risks")
    value = {
        "schema_version": FREEZE_SCHEMA, "campaign_digest": digest(campaign),
        "scenario_schema_version": "network_validation_scenario_v1",
        "generator_families": sorted({row["generator_family"] for row in campaign["scenarios"]}),
        "infrastructure_profiles": sorted(row["profile_id"] for row in campaign["infrastructure_profiles"]),
        "feature_contract_digest": environment["feature_contract_digest"], "feature_order": order,
        "model_configuration": campaign["candidate_identity"], "preprocessing_configuration": "network_features_v2",
        "class_map": ["benign", "auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"],
        "threshold_policy": "owner_decision_before_freeze", "metric_definitions": campaign["baseline_plan"][0]["metric_set"],
        "exclusion_rules": criteria["permitted_exclusions"], "acceptance_criteria": criteria,
        "split_policy": campaign["split_policy"], "environment_lock_digest": environment["canonical_digest"],
        "source_git_commit": source_commit, "compose_configuration_digest": compose_digest,
        "image_digests": {"client": environment["client_image_digest"], "targets": environment["target_image_digests"], "zeek": environment["zeek_image_digest"]},
        "unresolved_acceptance_fields": unresolved,
        "unresolved_integrity_fields": unresolved_integrity,
        "proxy_risks": risks,
        "sealable": not unresolved and not unresolved_integrity,
    }
    value["preview_sha256"] = digest(value)
    return value


def require_sealable(preview: dict[str, Any]) -> None:
    if not preview.get("sealable") or preview.get("unresolved_acceptance_fields") or preview.get("unresolved_integrity_fields"):
        raise ContractError("freeze preview contains unresolved fields")


def verify_sealed_bytes(data: bytes, expected_sha256: str) -> None:
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ContractError("sealed package integrity failure")
