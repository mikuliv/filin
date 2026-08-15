from __future__ import annotations

import copy
import json
from collections import Counter

import pytest

from lab.network_validation.contracts import ContractError, load_json
from lab.network_validation.phase1_execution_package import (
    CAMPAIGN_PATH,
    OFFICIAL_PACKAGE_PATH,
    PACKAGE_CONTRACT_PATHS,
    POLICY_PATH,
    RUN_PLAN_PATH,
    SCIENTIFIC_STATUS,
    SUPERSEDING_FREEZE_COMMIT,
    SUPERSEDING_FREEZE_PATH,
    audit_preflight,
    build_candidate_preview,
    build_run_plan,
    inspect_label_boundary,
    materialize_execution_inputs,
    official_payload,
    validate_candidate_preview,
    validate_official_package,
    validate_run_plan,
    validate_source_inputs,
    write_official_package,
)


def test_superseding_source_and_lineage_are_exact() -> None:
    value = validate_source_inputs()
    assert value["superseding_freeze_id"] == "network-validation-superseding-249104f7e7536356"
    assert value["superseding_freeze_digest"] == "249104f7e7536356621433f1b635c46967729164c58d53479770768372629d86"
    assert value["superseding_freeze_source_sha"] == "2377ab2cd12ead340d4f377aede9105635dbfe28"
    assert value["superseding_freeze_commit_sha"] == SUPERSEDING_FREEZE_COMMIT
    assert load_json(SUPERSEDING_FREEZE_PATH)["execution_protocol_complete"] is True


def test_run_plan_is_exact_complete_and_deterministic() -> None:
    first = build_run_plan()
    second = build_run_plan()
    assert first == second == load_json(RUN_PLAN_PATH)
    result = validate_run_plan(first)
    assert result["execution_sessions"] == 864
    assert result["execution_tokens_unique"] is True
    assert result["scientific_seeds_valid"] is True
    assert result["ordering_valid"] is True
    assert result["split_counts"] == {
        "blind_internal_holdout": 288,
        "development_calibration": 288,
        "development_train": 288,
    }
    assert result["run_plan_digest"] == "7f8109ed1b4d0216beae71c5999359bc67710629f66eedb977cb48d0142426df"
    assert result["exact_execution_order_digest"] == "be63a536b89eadad7d97ff63a40a314c37052452a8ce460b5ef1ac5e067588c2"


def test_each_scenario_has_exact_repetitions_seed_formula_and_split() -> None:
    units = load_json(RUN_PLAN_PATH)["ordered_execution_units"]
    by_scenario: dict[str, list[dict]] = {}
    for row in units:
        by_scenario.setdefault(row["scenario_token"], []).append(row)
        assert row["execution_seed"] == row["base_seed"] + row["repetition_index"] * 100000
    assert len(by_scenario) == 288
    assert all({row["repetition_index"] for row in rows} == {0, 1, 2} for rows in by_scenario.values())
    assert Counter(row["primary_split"] for row in units) == Counter({
        "development_train": 288,
        "development_calibration": 288,
        "blind_internal_holdout": 288,
    })


def test_frozen_matrix_counterfactuals_background_and_policy_are_preserved() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    policy = load_json(POLICY_PATH)
    assert len(campaign["scenario_templates"]) == 288
    assert len(campaign["counterfactual_pairs"]) == 24
    assert len({row["pair_id"] for row in campaign["counterfactual_pairs"]}) == 24
    assert Counter(row["background_policy"] for row in campaign["scenario_templates"]) == Counter({
        "http": 72, "dns": 72, "keepalive": 72, "combined": 72,
    })
    assert policy["technical_retry_policy"] == {
        "maximum_retries_per_execution": 1,
        "maximum_attempts_total": 2,
        "reason_allowlist": [
            "docker_daemon_transient_failure",
            "container_start_failure",
            "target_healthcheck_failure",
            "capture_start_failure",
            "capture_integrity_failure",
            "host_io_failure",
            "processing_integrity_failure",
        ],
        "preserve_failed_attempts": True,
    }
    assert policy["replacement_policy"] == {
        "scenario_substitution_allowed": False,
        "parameter_substitution_allowed": False,
        "replacement_with_different_seed_allowed": False,
        "retry_same_execution_identity": True,
    }
    assert policy["concurrency"] == 1
    assert policy["warmup_seconds"] == 2.0
    assert policy["capture_start_lead_seconds"] == policy["capture_stop_lag_seconds"] == 0.5
    assert policy["cooldown_seconds"] == 1.0
    assert policy["clock_offset_tolerance_ms"] == 500


def test_runner_evaluator_mapping_and_holdout_boundaries_are_fail_closed() -> None:
    boundary = inspect_label_boundary()
    assert boundary["runner_evaluator_separated"] is True
    assert boundary["forbidden_metadata_guard_passed"] is True
    assert boundary["label_vault_status"] == "absent_locked"
    assert boundary["labels_created"] is False and boundary["labels_unlocked"] is False
    runner = load_json(PACKAGE_CONTRACT_PATHS["runner_contract_digest"])
    evaluator = load_json(PACKAGE_CONTRACT_PATHS["evaluator_contract_digest"])
    mapping = load_json(PACKAGE_CONTRACT_PATHS["sealed_mapping_contract_digest"])
    assert set(runner["sensor_runtime"]["required_capabilities"]) == {"NET_RAW", "NET_ADMIN", "SETUID", "SETGID"}
    assert runner["sensor_runtime"]["privileged_allowed"] is False
    assert runner["sensor_runtime"]["docker_socket_mount_allowed"] is False
    assert runner["sensor_runtime"]["host_network_allowed"] is False
    assert evaluator["blind_internal_holdout_policy"] == {
        "campaign_controller_knows_assignment": True,
        "training_receives_feature_rows": False,
        "model_selection_receives_feature_rows": False,
        "calibration_uses_rows": False,
        "analyst_tuning_allowed": False,
    }
    assert mapping["mapping_key_storage"] == "external_secret"
    assert mapping["mapping_key_digest"] == "unresolved_until_secure_initialization"
    assert mapping["tracked_secret_allowed"] is False and mapping["mapping_created"] is False


def test_capture_output_and_session_integrity_contracts_are_strict() -> None:
    runner = load_json(PACKAGE_CONTRACT_PATHS["runner_contract_digest"])
    integrity = load_json(PACKAGE_CONTRACT_PATHS["session_integrity_contract_digest"])
    assert runner["capture_readiness_order"][:4] == [
        "capture_process_started", "capture_interface_open", "capture_ready_confirmed", "capture_process_alive",
    ]
    assert runner["capture_readiness_order"].index("scientific_traffic") > runner["capture_readiness_order"].index("capture_ready_confirmed")
    assert integrity["pcap_header_only_failure_code"] == "PCAP_HEADER_ONLY"
    assert integrity["zeek_conn_log_required"] is True
    assert integrity["feature_count_required"] == 51
    assert len(integrity["required_sha256_fields"]) == 10


def test_candidate_preview_is_valid_deterministic_and_non_executing() -> None:
    first = build_candidate_preview()
    second = build_candidate_preview()
    assert first == second
    assert first["candidate_valid"] is True
    assert first["official_execution_package_created"] is False
    assert first["execution_allowed"] is False
    assert first["execution_inputs_commit_sha"] == "unresolved_until_commit"
    assert first["blockers"] == ["execution_inputs_not_committed", "official_execution_package_not_created"]
    assert first["scientific_campaign_status"] == SCIENTIFIC_STATUS
    encoded = json.dumps(first)
    assert "created_at" not in encoded and "container_id" not in encoded
    assert validate_candidate_preview(first) == first


@pytest.mark.parametrize("field", [
    "superseding_freeze_digest",
    "superseding_freeze_commit_sha",
    "campaign_digest",
    "execution_policy_digest",
    "compose_runtime_digest",
    "split_assignments_digest",
    "run_plan_digest",
    "image_lock_digest",
    "feature_contract_digest",
    "feature_order_digest",
    "acceptance_criteria_digest",
    "runner_contract_digest",
    "evaluator_contract_digest",
    "label_vault_contract_digest",
    "output_contract_digest",
    "ledger_contract_digest",
    "preflight_contract_digest",
])
def test_candidate_tamper_detection(field: str) -> None:
    value = build_candidate_preview()
    value[field] = "0" * 64
    with pytest.raises(ContractError, match="integrity"):
        validate_candidate_preview(value)


def test_run_plan_tamper_detection() -> None:
    value = copy.deepcopy(load_json(RUN_PLAN_PATH))
    value["ordered_execution_units"][0]["execution_seed"] += 1
    with pytest.raises(ContractError, match="integrity"):
        validate_run_plan(value)


def test_official_payload_is_deterministic_and_write_is_guarded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "lab.network_validation.phase1_execution_package._validate_execution_inputs_commit",
        lambda source_sha: None,
    )
    source = "a" * 40
    created_at = "2026-08-16T00:00:00+07:00"
    first = official_payload(source, created_at)
    second = official_payload(source, created_at)
    assert first == second
    assert first["package_id"].startswith("network-validation-execution-")
    assert first["execution_plan_complete"] is True
    assert first["execution_allowed"] is False
    path = tmp_path / "official.json"
    with pytest.raises(ContractError, match="confirmation"):
        write_official_package(path, source, created_at, False)
    written = write_official_package(path, source, created_at, True)
    assert load_json(path) == written
    with pytest.raises(ContractError, match="overwritten"):
        write_official_package(path, source, created_at, True)


def test_official_package_when_present_validates_without_runtime_execution() -> None:
    if not OFFICIAL_PACKAGE_PATH.exists():
        pytest.skip("official package is created only after the execution inputs commit")
    value = validate_official_package()
    result = audit_preflight(value)
    assert result["official_execution_package_valid"] is True
    assert result["phase"] == "data_collection"
    assert result["runtime_preflight_required"] is True
    assert result["runtime_preflight_completed"] is False
    assert result["execution_allowed"] is False


def test_tooling_has_no_runtime_scientific_or_model_execution_path() -> None:
    source = (__import__("pathlib").Path(__file__).parents[2] / "lab/network_validation/phase1_execution_package.py").read_text(encoding="utf-8").lower()
    assert "docker run" not in source and "docker compose" not in source
    assert "tcpdump " not in source and "zeek -" not in source
    assert "model.fit" not in source and "unlock-labels" not in source
    assert "run-scientific-campaign" not in source and "execute-all" not in source
