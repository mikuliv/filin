from __future__ import annotations

import hashlib
import importlib.metadata
import locale
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any

from .causal_guard import feature_order
from .contracts import ENVIRONMENT_SCHEMA, FREEZE_SCHEMA, ContractError, canonical_bytes, digest, validate_campaign
from .freeze_candidate import counterfactual_pairs, expand_scenarios, freeze_candidate_proxy_risks, validate_acceptance_criteria, validate_freeze_candidate
from .image_lock import image_lock_blockers, validate_image_lock


def _command(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
        if result.returncode:
            return "unavailable"
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def _docker_client_version() -> str:
    value = _command(["docker", "version", "--format", "{{.Client.Version}}"])
    if value != "unavailable":
        return value
    fallback = _command(["docker", "--version"])
    match = re.search(r"Docker version ([0-9][0-9.]+)", fallback)
    return match.group(1) if match else "unavailable"


def validate_environment_lock(value: dict[str, Any]) -> None:
    required = {
        "schema_version", "os", "architecture", "python_version",
        "pip_dependency_lock_digest", "scikit_learn_version", "joblib_version",
        "docker_version", "docker_daemon_version", "docker_compose_version", "zeek_image_name",
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
        "docker_version": _docker_client_version(),
        "docker_daemon_version": _command(["docker", "version", "--format", "{{.Server.Version}}"]),
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


def freeze_candidate_preview(
    campaign: dict[str, Any],
    criteria: dict[str, Any],
    image_lock: dict[str, Any],
    environment: dict[str, Any],
    source_commit: str,
    root: Path,
) -> dict[str, Any]:
    validate_freeze_candidate(campaign)
    validate_acceptance_criteria(criteria)
    validate_image_lock(image_lock, root)
    validate_environment_lock(environment)
    if source_commit != environment["source_git_commit"]:
        raise ContractError("preview source commit mismatch")
    if campaign["acceptance_criteria_path"] != "lab/network_validation/config/acceptance_criteria.json" or campaign["image_lock_path"] != "lab/network_validation/config/image_lock.json":
        raise ContractError("freeze-candidate lock path mismatch")
    rows = expand_scenarios(campaign)
    pairs = counterfactual_pairs(campaign)
    risks = freeze_candidate_proxy_risks(campaign)
    seal_blockers = image_lock_blockers(image_lock)
    if environment["dirty_working_tree"]:
        seal_blockers.append("dirty_working_tree")
    if risks:
        seal_blockers.append("proxy_risk_warning")
    expected_absences = [
        "scientific_corpus_not_collected",
        "external_corpus_result_missing",
        "model_not_trained",
        "evaluation_not_performed",
        "labels_not_unlocked",
    ]
    scientific_pass_requirements = [
        "campaign_completed",
        "predictions_frozen_before_label_unlock",
        "evaluation_completed",
        "acceptance_criteria_passed",
        "external_corpus_result_passed",
    ]
    order = feature_order()
    value = {
        "schema_version": "network_validation_freeze_candidate_preview_v1",
        "official_freeze_created": False,
        "experiment_started": False,
        "source_git_commit": source_commit,
        "dirty_working_tree": environment["dirty_working_tree"],
        "campaign_plan_digest": digest(campaign),
        "scenario_schema_digest": hashlib.sha256(root.joinpath("lab/network_validation/contracts.py").read_bytes()).hexdigest(),
        "scenario_matrix_digest": digest(rows),
        "scenario_count": len(rows),
        "generator_families": sorted({row["scenario"]["generator_family"] for row in rows}),
        "infrastructure_profiles": sorted({row["scenario"]["infrastructure_profile"] for row in rows}),
        "target_implementations": sorted({row["target_implementation"] for row in rows}),
        "feature_contract_digest": environment["feature_contract_digest"],
        "feature_order_digest": environment["feature_order_digest"],
        "acceptance_criteria_digest": criteria["canonical_digest"],
        "split_policy_digest": digest(campaign["split_policy"]),
        "counterfactual_plan_digest": digest(pairs),
        "counterfactual_pair_count": len(pairs),
        "image_lock_digest": image_lock["canonical_digest"],
        "environment_lock": environment,
        "proxy_risks": risks,
        "seal_blockers": sorted(set(seal_blockers)),
        "expected_pre_experiment_absences": expected_absences,
        "scientific_pass_requirements": scientific_pass_requirements,
        "scientific_pass_allowed": False,
        "seal_allowed": not seal_blockers,
        "sealable": not seal_blockers,
    }
    value["preview_sha256"] = digest(value)
    return value


OFFICIAL_FREEZE_SCHEMA = "network_validation_official_freeze_v1"
OFFICIAL_FREEZE_FIELDS = {
    "schema_version", "freeze_id", "created_at", "source_git_sha", "source_tree_clean",
    "campaign_plan_digest", "campaign_matrix_digest", "counterfactual_plan_digest",
    "split_policy_digest", "acceptance_criteria_digest", "feature_contract_digest",
    "feature_order_digest", "image_lock_digest", "environment_lock_digest",
    "generator_families", "infrastructure_profiles", "target_implementations",
    "required_images", "proxy_validation_result", "seal_preconditions",
    "expected_pre_experiment_absences", "scientific_pass_requirements",
    "production_approval", "canonical_payload_sha256",
}


def official_freeze_identity(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"created_at", "canonical_payload_sha256"}}


def official_freeze_payload(
    preview: dict[str, Any], environment: dict[str, Any], image_lock: dict[str, Any],
    source_git_sha: str, created_at: str,
) -> dict[str, Any]:
    if not preview.get("seal_allowed") or preview.get("seal_blockers"):
        raise ContractError("official freeze has unresolved seal blockers")
    if preview.get("source_git_commit") != source_git_sha or environment.get("source_git_commit") != source_git_sha:
        raise ContractError("official freeze source Git SHA mismatch")
    if environment.get("dirty_working_tree"):
        raise ContractError("official freeze requires a clean source tree")
    images = {row["logical_name"]: row for row in image_lock["images"]}
    required_images = {
        name: {
            "platform_manifest_digest": row["platform_manifest_digest"],
            "config_digest": row["config_digest"],
            "verification_status": row["verification_status"],
        }
        for name, row in images.items()
    }
    value = {
        "schema_version": OFFICIAL_FREEZE_SCHEMA,
        "created_at": created_at,
        "source_git_sha": source_git_sha,
        "source_tree_clean": True,
        "campaign_plan_digest": preview["campaign_plan_digest"],
        "campaign_matrix_digest": preview["scenario_matrix_digest"],
        "counterfactual_plan_digest": preview["counterfactual_plan_digest"],
        "split_policy_digest": preview["split_policy_digest"],
        "acceptance_criteria_digest": preview["acceptance_criteria_digest"],
        "feature_contract_digest": preview["feature_contract_digest"],
        "feature_order_digest": preview["feature_order_digest"],
        "image_lock_digest": preview["image_lock_digest"],
        "environment_lock_digest": environment["canonical_digest"],
        "generator_families": preview["generator_families"],
        "infrastructure_profiles": preview["infrastructure_profiles"],
        "target_implementations": preview["target_implementations"],
        "required_images": required_images,
        "proxy_validation_result": {"passed": True, "warning_count": 0, "warnings": []},
        "seal_preconditions": {
            "seal_allowed": True, "seal_blockers": [],
            "scenario_count": preview["scenario_count"],
            "counterfactual_pair_count": preview["counterfactual_pair_count"],
            "campaign_status": "not_started", "labels_status": "locked_or_not_created",
            "model_status": "not_trained", "scientific_metrics_status": "not_calculated",
            "external_evaluation_status": "pending_post_experiment",
        },
        "expected_pre_experiment_absences": preview["expected_pre_experiment_absences"],
        "scientific_pass_requirements": preview["scientific_pass_requirements"],
        "production_approval": False,
    }
    value["freeze_id"] = f"network-validation-{digest({key: item for key, item in value.items() if key != 'created_at'})[:16]}"
    value["canonical_payload_sha256"] = digest(official_freeze_identity(value))
    return value


def validate_official_freeze(
    value: dict[str, Any], campaign: dict[str, Any], criteria: dict[str, Any],
    image_lock: dict[str, Any], environment: dict[str, Any], source_git_sha: str, root: Path,
) -> dict[str, Any]:
    if set(value) != OFFICIAL_FREEZE_FIELDS or value.get("schema_version") != OFFICIAL_FREEZE_SCHEMA:
        raise ContractError("official freeze fields mismatch")
    preview = freeze_candidate_preview(campaign, criteria, image_lock, environment, source_git_sha, root)
    expected = official_freeze_payload(preview, environment, image_lock, source_git_sha, value["created_at"])
    if value != expected:
        raise ContractError("official freeze does not match current sealed inputs")
    return value


def write_official_freeze(path: Path, value: dict[str, Any], *, confirmed: bool) -> None:
    if not confirmed:
        raise ContractError("explicit official-freeze confirmation is required")
    if path.exists():
        raise ContractError("official freeze overwrite is forbidden")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def require_sealable(preview: dict[str, Any]) -> None:
    if not preview.get("sealable") or preview.get("unresolved_acceptance_fields") or preview.get("unresolved_integrity_fields"):
        raise ContractError("freeze preview contains unresolved fields")


def verify_sealed_bytes(data: bytes, expected_sha256: str) -> None:
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ContractError("sealed package integrity failure")
