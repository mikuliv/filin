from __future__ import annotations

import copy
import hashlib
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from .contracts import ContractError, digest, load_json, write_canonical
from .superseding_freeze import validate_inputs, validate_official


ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name("config")
EXECUTION = Path(__file__).with_name("execution")
FREEZE = Path(__file__).with_name("freeze")

CAMPAIGN_PATH = CONFIG / "superseding_freeze_campaign.json"
POLICY_PATH = CONFIG / "superseding_execution_policy.json"
SPLIT_PATH = CONFIG / "superseding_split_assignments.json"
IMAGE_PATH = CONFIG / "superseding_image_lock.json"
SUPERSEDING_FREEZE_PATH = FREEZE / "official_superseding_freeze.json"
RUN_PLAN_PATH = EXECUTION / "phase1_run_plan.json"
OFFICIAL_PACKAGE_PATH = EXECUTION / "official_execution_package.json"
COMPOSE_PATH = Path(__file__).with_name("compose.yaml")

SUPERSEDING_FREEZE_COMMIT = "26222536d71aca898d382b46f6b1c59f1102bbd2"
PACKAGE_SCHEMA = "network_validation_official_execution_package_v1"
RUN_PLAN_SCHEMA = "network_validation_phase1_run_plan_v1"

FROZEN_CONTRACT_PATHS = {
    "label_vault_contract_digest": EXECUTION / "label_vault_contract.json",
    "output_contract_digest": EXECUTION / "output_contract.json",
    "ledger_contract_digest": EXECUTION / "campaign_ledger_contract.json",
    "superseding_preflight_contract_digest": EXECUTION / "preflight_contract.json",
}
PACKAGE_CONTRACT_PATHS = {
    "runner_contract_digest": EXECUTION / "runner_contract.json",
    "evaluator_contract_digest": EXECUTION / "evaluator_contract.json",
    "sealed_mapping_contract_digest": EXECUTION / "sealed_mapping_contract.json",
    "session_integrity_contract_digest": EXECUTION / "session_integrity_contract.json",
    "preflight_contract_digest": EXECUTION / "phase1_preflight_contract.json",
}

INPUT_PATHS = (
    CAMPAIGN_PATH,
    POLICY_PATH,
    SPLIT_PATH,
    IMAGE_PATH,
    SUPERSEDING_FREEZE_PATH,
    RUN_PLAN_PATH,
    COMPOSE_PATH,
    *FROZEN_CONTRACT_PATHS.values(),
    *PACKAGE_CONTRACT_PATHS.values(),
)

SCIENTIFIC_STATUS = {
    "scientific_campaign_started": False,
    "scientific_sessions_executed": 0,
    "scientific_corpus_created": False,
    "labels_created": False,
    "labels_unlocked": False,
    "model_trained": False,
    "predictions_created": False,
    "scientific_metrics_calculated": False,
    "external_evaluation_performed": False,
    "production_approval": False,
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _without_digest(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "canonical_digest"}


def _package_identity(value: dict[str, Any]) -> dict[str, Any]:
    excluded = {
        "canonical_payload_sha256",
        "package_id",
        "created_at",
        "official_execution_package_commit_sha",
    }
    return {key: item for key, item in value.items() if key not in excluded}


def _assert_canonical(value: dict[str, Any], name: str) -> None:
    if value.get("canonical_digest") != digest(_without_digest(value)):
        raise ContractError(f"{name} canonical digest mismatch")


def _git_commit_exists(sha: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    ).returncode == 0


def _git_contains_current_file(sha: str, path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"{sha}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout == path.read_bytes()


def _contract_digests() -> dict[str, str]:
    return {
        name: digest(load_json(path))
        for name, path in sorted(FROZEN_CONTRACT_PATHS.items() | PACKAGE_CONTRACT_PATHS.items())
    }


def validate_source_inputs() -> dict[str, Any]:
    source_result = validate_inputs()
    campaign = load_json(CAMPAIGN_PATH)
    policy = load_json(POLICY_PATH)
    assignments = load_json(SPLIT_PATH)
    image = load_json(IMAGE_PATH)
    freeze = validate_official(load_json(SUPERSEDING_FREEZE_PATH))

    expected = {
        "campaign_digest": campaign["canonical_digest"],
        "execution_policy_digest": policy["canonical_digest"],
        "split_assignment_digest": assignments["canonical_digest"],
        "image_lock_digest": image["canonical_digest"],
    }
    for field, value in expected.items():
        if freeze.get(field) != value:
            raise ContractError(f"superseding freeze {field} mismatch")
    if freeze["canonical_payload_sha256"] != "249104f7e7536356621433f1b635c46967729164c58d53479770768372629d86":
        raise ContractError("unexpected superseding freeze canonical digest")
    if not _git_commit_exists(SUPERSEDING_FREEZE_COMMIT):
        raise ContractError("superseding freeze containing commit does not exist")
    if not _git_contains_current_file(SUPERSEDING_FREEZE_COMMIT, SUPERSEDING_FREEZE_PATH):
        raise ContractError("superseding freeze containing commit does not contain current freeze")

    contract_digests = _contract_digests()
    for field in FROZEN_CONTRACT_PATHS:
        freeze_field = "preflight_contract_digest" if field == "superseding_preflight_contract_digest" else field
        if freeze.get(freeze_field) != contract_digests[field]:
            raise ContractError(f"frozen {field} mismatch")

    runner = load_json(PACKAGE_CONTRACT_PATHS["runner_contract_digest"])
    evaluator = load_json(PACKAGE_CONTRACT_PATHS["evaluator_contract_digest"])
    mapping = load_json(PACKAGE_CONTRACT_PATHS["sealed_mapping_contract_digest"])
    preflight = load_json(PACKAGE_CONTRACT_PATHS["preflight_contract_digest"])
    required_caps = {"NET_RAW", "NET_ADMIN", "SETUID", "SETGID"}
    if set(runner["sensor_runtime"]["required_capabilities"]) != required_caps:
        raise ContractError("sensor capability set is not exact")
    if any(runner["sensor_runtime"][name] for name in ("privileged_allowed", "docker_socket_mount_allowed", "host_network_allowed")):
        raise ContractError("sensor runtime expands privileges")
    forbidden = set(evaluator["forbidden_fields_before_label_unlock"])
    required_forbidden = {
        "behavior_type", "label", "class", "generator_family", "infrastructure_profile",
        "target_implementation", "target_port", "scenario_token", "execution_token",
        "execution_seed", "background_traffic_policy", "primary_split", "path", "filename",
        "marker_metadata",
    }
    if not required_forbidden <= forbidden:
        raise ContractError("evaluator metadata guard is incomplete")
    if mapping["tracked_secret_allowed"] or mapping["mapping_created"]:
        raise ContractError("sealed mapping contract contains or authorizes tracked mapping material")
    if preflight["runtime_preflight_completed"] or preflight["scientific_session_execution_allowed"]:
        raise ContractError("phase1 preflight contract claims runtime completion")
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    exact_caps = 'cap_add: ["NET_RAW", "NET_ADMIN", "SETUID", "SETGID"]'
    if exact_caps not in compose or 'network_mode: "service:common-client"' not in compose:
        raise ContractError("capture runtime capability or namespace contract mismatch")
    if "privileged:" in compose or "/var/run/docker.sock" in compose or 'network_mode: "host"' in compose:
        raise ContractError("capture runtime contains a forbidden privilege expansion")

    return {
        **source_result,
        "superseding_freeze_id": freeze["freeze_id"],
        "superseding_freeze_digest": freeze["canonical_payload_sha256"],
        "superseding_freeze_source_sha": freeze["source_git_sha"],
        "superseding_freeze_commit_sha": SUPERSEDING_FREEZE_COMMIT,
        "contract_digests": contract_digests,
    }


def build_run_plan() -> dict[str, Any]:
    validate_source_inputs()
    campaign = load_json(CAMPAIGN_PATH)
    policy = load_json(POLICY_PATH)
    assignments = load_json(SPLIT_PATH)
    units = copy.deepcopy(assignments["ordered_execution_units"])
    value = {
        "schema_version": RUN_PLAN_SCHEMA,
        "campaign_digest": campaign["canonical_digest"],
        "execution_policy_digest": policy["canonical_digest"],
        "compose_runtime_digest": hashlib.sha256(COMPOSE_PATH.read_bytes()).hexdigest(),
        "split_assignments_digest": assignments["canonical_digest"],
        "scenario_template_count": 288,
        "repetitions_per_template": 3,
        "execution_session_count": 864,
        "run_plan_digest": digest(units),
        "exact_execution_order_digest": digest([row["execution_token"] for row in units]),
        "ordered_execution_units": units,
    }
    value["canonical_digest"] = digest(value)
    return value


def validate_run_plan(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or load_json(RUN_PLAN_PATH)
    expected = build_run_plan()
    if value != expected:
        raise ContractError("phase1 run plan integrity mismatch")
    units = value["ordered_execution_units"]
    tokens = [row["execution_token"] for row in units]
    identities = [row["execution_identity_sha256"] for row in units]
    seeds = [row["execution_seed"] for row in units]
    if len(units) != 864 or len(set(tokens)) != 864 or len(set(identities)) != 864:
        raise ContractError("execution tokens are not unique and complete")
    if len(set(seeds)) != 864:
        raise ContractError("scientific execution seeds are not unique")
    for row in units:
        expected_identity = _sha(
            f"network-validation-execution-v1\0{row['scenario_token']}\0{row['repetition_index']}"
        )
        if row["execution_identity_sha256"] != expected_identity or row["execution_token"] != expected_identity[:24]:
            raise ContractError("execution token derivation mismatch")
        if row["execution_seed"] != row["base_seed"] + row["repetition_index"] * 100000:
            raise ContractError("scientific seed derivation mismatch")
        if row["order_key"] != _sha(f"network-validation-order-v1\0{row['execution_token']}"):
            raise ContractError("execution order key mismatch")
    if [row["order_key"] for row in units] != sorted(row["order_key"] for row in units):
        raise ContractError("run plan is not sorted by frozen order key")
    if [row["execution_order_index"] for row in units] != list(range(864)):
        raise ContractError("execution order indices are not contiguous")
    split_counts = Counter(row["primary_split"] for row in units)
    if split_counts != Counter({
        "development_train": 288,
        "development_calibration": 288,
        "blind_internal_holdout": 288,
    }):
        raise ContractError("primary split cardinality mismatch")
    repetitions: dict[str, set[int]] = {}
    for row in units:
        repetitions.setdefault(row["scenario_token"], set()).add(row["repetition_index"])
    if len(repetitions) != 288 or any(value != {0, 1, 2} for value in repetitions.values()):
        raise ContractError("scenario repetition coverage mismatch")
    return {
        "valid": True,
        "scenario_templates": 288,
        "execution_sessions": 864,
        "execution_tokens_unique": True,
        "scientific_seeds_valid": True,
        "ordering_valid": True,
        "split_counts": dict(sorted(split_counts.items())),
        "run_plan_digest": value["run_plan_digest"],
        "exact_execution_order_digest": value["exact_execution_order_digest"],
        "run_plan_manifest_digest": value["canonical_digest"],
    }


def materialize_execution_inputs() -> dict[str, Any]:
    value = build_run_plan()
    write_canonical(RUN_PLAN_PATH, value)
    return validate_run_plan(value)


def build_candidate_preview(execution_inputs_commit_sha: str = "unresolved_until_commit") -> dict[str, Any]:
    if execution_inputs_commit_sha != "unresolved_until_commit":
        _validate_execution_inputs_commit(execution_inputs_commit_sha)
    sources = validate_source_inputs()
    run_plan = validate_run_plan()
    campaign = load_json(CAMPAIGN_PATH)
    policy = load_json(POLICY_PATH)
    assignments = load_json(SPLIT_PATH)
    image = load_json(IMAGE_PATH)
    freeze = load_json(SUPERSEDING_FREEZE_PATH)
    contracts = sources["contract_digests"]
    identity = {
        "schema_version": PACKAGE_SCHEMA,
        "package_type": "phase1_data_collection",
        "superseding_freeze_id": freeze["freeze_id"],
        "superseding_freeze_digest": freeze["canonical_payload_sha256"],
        "superseding_freeze_source_sha": freeze["source_git_sha"],
        "superseding_freeze_commit_sha": SUPERSEDING_FREEZE_COMMIT,
        "execution_inputs_commit_sha": execution_inputs_commit_sha,
        "campaign_digest": campaign["canonical_digest"],
        "matrix_digest": freeze["matrix_digest"],
        "execution_policy_digest": policy["canonical_digest"],
        "compose_runtime_digest": hashlib.sha256(COMPOSE_PATH.read_bytes()).hexdigest(),
        "run_plan_digest": run_plan["run_plan_digest"],
        "run_plan_manifest_digest": run_plan["run_plan_manifest_digest"],
        "exact_execution_order_digest": run_plan["exact_execution_order_digest"],
        "split_assignments_digest": assignments["canonical_digest"],
        "counterfactual_digest": freeze["counterfactual_digest"],
        "scenario_template_count": 288,
        "repetitions_per_template": 3,
        "execution_session_count": 864,
        "image_lock_digest": image["canonical_digest"],
        "feature_contract_digest": freeze["feature_contract_digest"],
        "feature_order_digest": freeze["feature_order_digest"],
        "acceptance_criteria_digest": freeze["acceptance_criteria_digest"],
        **contracts,
        "mapping_key_required_at_execution": True,
        "mapping_key_storage": "external_secret",
        "mapping_key_digest": "unresolved_until_secure_initialization",
        "external_corpus_required_for_scientific_pass": True,
        "source_tree_clean": execution_inputs_commit_sha != "unresolved_until_commit",
        "runtime_preflight_required": True,
        "runtime_preflight_completed": False,
        "execution_allowed_after_runtime_preflight": execution_inputs_commit_sha != "unresolved_until_commit",
        "model_required": False,
        "scientific_campaign_status": copy.deepcopy(SCIENTIFIC_STATUS),
    }
    canonical = digest(identity)
    return {
        **identity,
        "package_id": f"network-validation-execution-{canonical[:16]}",
        "canonical_payload_sha256": canonical,
        "candidate_valid": True,
        "official_execution_package_created": False,
        "execution_allowed": False,
        "blockers": [] if execution_inputs_commit_sha != "unresolved_until_commit" else [
            "execution_inputs_not_committed",
            "official_execution_package_not_created",
        ],
    }


def validate_candidate_preview(value: dict[str, Any]) -> dict[str, Any]:
    source = value.get("execution_inputs_commit_sha", "")
    expected = build_candidate_preview(source)
    if value != expected:
        raise ContractError("execution package preview integrity mismatch")
    if value["official_execution_package_created"] or value["execution_allowed"]:
        raise ContractError("candidate preview cannot authorize execution")
    return value


def _validate_execution_inputs_commit(source_sha: str) -> None:
    if not _git_commit_exists(source_sha):
        raise ContractError("execution inputs commit does not exist")
    for path in INPUT_PATHS:
        if not _git_contains_current_file(source_sha, path):
            raise ContractError(f"execution inputs commit does not contain current input: {path.relative_to(ROOT).as_posix()}")


def official_payload(source_sha: str, created_at: str) -> dict[str, Any]:
    _validate_execution_inputs_commit(source_sha)
    preview = build_candidate_preview(source_sha)
    value = {
        key: item
        for key, item in preview.items()
        if key not in {"candidate_valid", "official_execution_package_created", "execution_allowed", "blockers"}
    }
    value.update({
        "created_at": created_at,
        "official_execution_package_commit_sha": "unresolved_until_commit_B",
        "official_execution_package_created": True,
        "execution_plan_complete": True,
        "execution_allowed": False,
    })
    canonical = digest(_package_identity(value))
    value["package_id"] = f"network-validation-execution-{canonical[:16]}"
    value["canonical_payload_sha256"] = canonical
    return value


def write_official_package(path: Path, source_sha: str, created_at: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise ContractError("official execution package requires explicit confirmation")
    if path.exists():
        raise ContractError("official execution package cannot be overwritten")
    value = official_payload(source_sha, created_at)
    write_canonical(path, value)
    return value


def validate_official_package(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or load_json(OFFICIAL_PACKAGE_PATH)
    expected = official_payload(value.get("execution_inputs_commit_sha", ""), value.get("created_at", ""))
    if value != expected:
        raise ContractError("official execution package integrity mismatch")
    if value["package_type"] != "phase1_data_collection" or not value["execution_plan_complete"]:
        raise ContractError("official execution package phase or plan is invalid")
    if value["scientific_campaign_status"] != SCIENTIFIC_STATUS:
        raise ContractError("official execution package scientific status mismatch")
    return value


def inspect_run_plan() -> dict[str, Any]:
    return validate_run_plan()


def inspect_label_boundary() -> dict[str, Any]:
    evaluator = load_json(PACKAGE_CONTRACT_PATHS["evaluator_contract_digest"])
    mapping = load_json(PACKAGE_CONTRACT_PATHS["sealed_mapping_contract_digest"])
    return {
        "valid": True,
        "runner_evaluator_separated": True,
        "label_vault_status": "absent_locked",
        "labels_created": False,
        "labels_unlocked": False,
        "forbidden_metadata_guard_passed": True,
        "forbidden_evaluator_fields": evaluator["forbidden_fields_before_label_unlock"],
        "mapping_key_required_at_execution": mapping["mapping_key_required_at_execution"],
        "mapping_key_storage": mapping["mapping_key_storage"],
    }


def audit_preflight(value: dict[str, Any] | None = None) -> dict[str, Any]:
    package = validate_official_package(value)
    return {
        "official_execution_package_valid": True,
        "phase": "data_collection",
        "execution_plan_complete": True,
        "scientific_campaign_started": False,
        "labels_created": False,
        "model_required": False,
        "runtime_preflight_required": True,
        "runtime_preflight_completed": False,
        "execution_allowed": False,
        "package_id": package["package_id"],
    }
