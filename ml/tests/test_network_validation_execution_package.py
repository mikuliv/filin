from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lab.network_validation.contracts import ContractError, load_json
from lab.network_validation.execution_package import (
    BLOCKED_STATUS,
    CONTRACT_DIR,
    audit_execution_readiness,
    build_execution_package_preview,
    inspect_label_boundary,
    inspect_run_plan,
    validate_execution_package_preview,
)
from lab.network_validation.freeze_candidate import expand_scenarios


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "lab/network_validation/config/freeze_candidate_campaign.json"
OFFICIAL_FREEZE = ROOT / "lab/network_validation/freeze/official_freeze.json"


def campaign() -> dict:
    return load_json(CAMPAIGN)


def official_freeze() -> dict:
    return load_json(OFFICIAL_FREEZE)


def test_official_freeze_is_immutable_and_source_sha_is_not_containing_commit() -> None:
    assert subprocess.run(["git", "diff", "--exit-code", "--", str(OFFICIAL_FREEZE)], cwd=ROOT, check=False).returncode == 0
    freeze = official_freeze()
    containing_commit = "a955ce3fdb1387266a9f1eb21a6e4db6b0a3eed8"
    assert freeze["source_git_sha"] == "a6a979aef803ba776933b39dbd7607bd0833cc63"
    assert subprocess.run(["git", "merge-base", "--is-ancestor", containing_commit, "HEAD"], cwd=ROOT, check=False).returncode == 0
    assert freeze["source_git_sha"] != containing_commit
    assert freeze["canonical_payload_sha256"] == "870946390f9ca8a5fe0ac2c53e7855e979ef242d9486815ef67d6d47ca9cbe41"


def test_readiness_detects_all_execution_affecting_freeze_gaps() -> None:
    value = audit_execution_readiness(campaign(), official_freeze())
    assert value["status"] == BLOCKED_STATUS
    assert value["complete_for_execution"] is False and value["execution_allowed"] is False
    assert {
        "scientific_repetition_policy", "execution_order_policy", "execution_concurrency_policy",
        "session_isolation_reset_policy", "warmup_and_cooldown_policy",
        "capture_start_lead_and_stop_lag", "clock_offset_tolerance",
        "campaign_retry_and_replacement_policy", "exclusion_reason_allowlist",
        "exact_split_assignments", "output_and_session_integrity_schema",
    } <= set(value["gaps"])
    fields = {row["field"]: row for row in value["fields"]}
    assert fields["scientific_seed_values"]["frozen"] is True
    assert fields["scientific_repetition_policy"]["frozen"] is False


def test_order_is_scientifically_significant_and_must_not_be_inferred_from_matrix_order() -> None:
    field = next(row for row in audit_execution_readiness(campaign(), official_freeze())["fields"] if row["field"] == "execution_order_policy")
    assert field["frozen"] is False
    assert "carry-over" in field["scientific_significance"]
    assert inspect_run_plan(campaign(), official_freeze())["run_plan_materialized"] is False


def test_frozen_matrix_preserves_72_templates_24_pairs_and_unique_tokens() -> None:
    rows = expand_scenarios(campaign())
    assert len(rows) == len({row["scenario"]["scenario_token"] for row in rows}) == 72
    assert len({row["session_token"] for row in rows}) == 72
    assert [row["scenario"]["seed"] for row in rows] == list(range(1000, 1072))
    assert official_freeze()["seal_preconditions"]["counterfactual_pair_count"] == 24


def test_blocked_preview_is_canonical_deterministic_and_has_no_run_plan() -> None:
    first = build_execution_package_preview(campaign(), official_freeze())
    second = build_execution_package_preview(campaign(), official_freeze())
    assert first == second
    assert first["canonical_digest"] == second["canonical_digest"]
    assert first["candidate_created"] is False
    assert first["official_execution_package"] is False
    assert first["execution_package_commit_sha"] == "unresolved_until_commit"
    assert first["scenario_templates"] == 72 and first["execution_sessions"] == 0
    assert first["run_plan_materialized"] is False and first["execution_allowed"] is False
    encoded = json.dumps(first)
    assert "created_at" not in encoded and "local_image_id" not in encoded and str(ROOT) not in encoded
    assert validate_execution_package_preview(first) == first


def test_preview_tamper_is_rejected() -> None:
    value = build_execution_package_preview(campaign(), official_freeze())
    value["blockers"] = []
    with pytest.raises(ContractError, match="integrity"):
        validate_execution_package_preview(value)
    value = build_execution_package_preview(campaign(), official_freeze())
    value["execution_allowed"] = True
    with pytest.raises(ContractError, match="cannot authorize"):
        validate_execution_package_preview(value)


def test_label_boundary_is_empty_locked_and_filters_runner_metadata() -> None:
    value = inspect_label_boundary()
    assert value["runner_evaluator_separated"] is True
    assert value["label_vault_status"] == "absent_locked"
    assert value["labels_created"] is False and value["labels_unlocked"] is False
    assert value["forbidden_metadata_guard_passed"] is True
    assert {"behavior_type", "generator_family", "scenario_token", "seed", "session_token", "split_assignment"} <= set(value["forbidden_evaluator_fields"])


def test_output_ledger_and_preflight_contracts_are_fail_closed() -> None:
    output = load_json(CONTRACT_DIR / "output_contract.json")
    ledger = load_json(CONTRACT_DIR / "campaign_ledger_contract.json")
    preflight = load_json(CONTRACT_DIR / "preflight_contract.json")
    assert {"labels", "predictions", "scientific_metrics", "trained_model"} == set(output["forbidden_outputs"])
    assert "docker_daemon_transient_failure" in ledger["retry_reason_allowlist"]
    assert "capture_integrity_failure" in ledger["exclusion_reason_allowlist"]
    assert ledger["reason_policy_status"] == "frozen_by_superseding_execution_policy"
    assert preflight["current_expected_result"] == {
        "execution_allowed": False,
        "status": "SUPERSEDING_INPUTS_REQUIRE_CLEAN_COMMIT_AND_OFFICIAL_FREEZE",
    }


def test_preview_module_has_no_execution_or_scientific_artifact_path() -> None:
    source = (ROOT / "lab/network_validation/execution_package.py").read_text(encoding="utf-8").lower()
    assert "docker compose up" not in source and "docker run" not in source
    assert "tcpdump" not in source and "zeek -" not in source
    assert ".pcap" not in source and "model.fit" not in source
    assert "write_text" not in source and "write_bytes" not in source
