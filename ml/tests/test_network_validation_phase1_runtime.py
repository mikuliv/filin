from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab.network_validation.cli import parser
from lab.network_validation.contracts import ContractError, load_json
from lab.network_validation.operational_initialization import evaluation_token
from lab.network_validation.phase1_docker_runner import (
    Phase1DockerRunner,
    TechnicalFailure,
)
from lab.network_validation.phase1_execution_package import RUN_PLAN_PATH
from lab.network_validation.phase1_runtime import (
    LedgerStore,
    MappingStore,
    SessionPaths,
    derive_attempt_id,
    derive_runtime_namespace,
    derive_session_token,
    runtime_contract_digest,
    session_identity,
    validate_runtime_contract,
)
from lab.network_validation.runtime_execution_package import (
    build_payload,
    build_preview,
    validate_package,
    write_official_package,
)
from lab.network_validation.superseding_execution_package import (
    OFFICIAL_PACKAGE_V2_PATH,
    SCIENTIFIC_DIGEST_FIELDS,
)

PACKAGE = {
    "package_id": "network-validation-execution-" + "a" * 16,
    "canonical_digest": "b" * 64,
    "feature_contract_digest": "c" * 64,
    "feature_order_digest": "d" * 64,
}


def _first_unit() -> dict[str, object]:
    return load_json(RUN_PLAN_PATH)["ordered_execution_units"][0]


def test_runtime_contract_is_complete_and_non_scientific() -> None:
    value = validate_runtime_contract()
    assert value["scientific_protocol_changed"] is False
    assert value["mapping_lifecycle"]["precompute_future_entries"] is False
    assert value["stop_gate"]["maximum_completed_units_per_invocation"] == 1
    assert len(runtime_contract_digest()) == 64
    assert len(value["artifact_schemas"]) == 10


def test_session_attempt_and_namespace_identity_is_deterministic() -> None:
    unit = _first_unit()
    token = str(unit["execution_token"])
    session = derive_session_token(PACKAGE["package_id"], token)
    first = derive_attempt_id(PACKAGE["package_id"], token, 1)
    second = derive_attempt_id(PACKAGE["package_id"], token, 2)
    assert len(session) == len(first) == len(second) == 24
    assert first != second
    namespace = derive_runtime_namespace(PACKAGE["canonical_digest"], first)
    assert namespace.startswith("filin-nv-") and len(namespace) <= 63
    assert session_identity(PACKAGE, unit, 1).runtime_namespace == namespace


def test_ledger_lifecycle_is_append_only_ordered_and_chained(tmp_path: Path) -> None:
    ledger_path = tmp_path / "campaign-ledger.jsonl"
    ledger_path.write_bytes(b"")
    store = LedgerStore(ledger_path, PACKAGE["package_id"], PACKAGE["canonical_digest"])
    unit = _first_unit()
    first = session_identity(PACKAGE, unit, 1)
    store.append(first, "session_started", occurred_at="2026-01-01T00:00:00Z")
    store.append(first, "session_failed", reason_code="capture_integrity_failure", occurred_at="2026-01-01T00:00:01Z")
    store.append(first, "retry_requested", reason_code="capture_integrity_failure", occurred_at="2026-01-01T00:00:02Z")
    second = session_identity(PACKAGE, unit, 2)
    store.append(second, "session_started", occurred_at="2026-01-01T00:00:03Z")
    store.append(second, "session_completed", occurred_at="2026-01-01T00:00:04Z")
    records = store.read()
    assert [row["record_sequence"] for row in records] == [1, 2, 3, 4, 5]
    assert all(records[index]["previous_record_digest"] == records[index - 1]["record_digest"] for index in range(1, 5))
    assert store.attempts_for(str(unit["execution_token"])) == 2
    assert store.completed_tokens() == {unit["execution_token"]}


def test_ledger_rejects_invalid_transition_and_wrong_run_plan_order(tmp_path: Path) -> None:
    ledger_path = tmp_path / "campaign-ledger.jsonl"
    ledger_path.write_bytes(b"")
    store = LedgerStore(ledger_path, PACKAGE["package_id"], PACKAGE["canonical_digest"])
    unit = _first_unit()
    identity = session_identity(PACKAGE, unit, 1)
    with pytest.raises(ContractError):
        store.append(identity, "session_completed", occurred_at="2026-01-01T00:00:00Z")
    second_unit = load_json(RUN_PLAN_PATH)["ordered_execution_units"][1]
    with pytest.raises(ContractError):
        store.append(session_identity(PACKAGE, second_unit, 1), "session_started", occurred_at="2026-01-01T00:00:00Z")
    assert ledger_path.read_bytes() == b""


def test_mapping_entry_is_lazy_idempotent_and_secret_bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lab.network_validation.phase1_runtime._restrict_windows_acl", lambda _: None)
    secret = bytes(range(32))
    token = str(_first_unit()["execution_token"])
    store = MappingStore(tmp_path, PACKAGE["package_id"], PACKAGE["canonical_digest"], secret)
    assert store.read() == [] and not store.path.exists()
    first = store.ensure(token, created_at="2026-01-01T00:00:00Z")
    second = store.ensure(token, created_at="2026-01-02T00:00:00Z")
    assert first == second
    assert first["evaluation_token"] == evaluation_token(secret, token)
    assert len(store.read()) == 1
    raw = store.path.read_bytes()
    assert raw.endswith(b"\n") and b"\r" not in raw
    assert json.loads(raw)["execution_token"] == token


def test_mapping_acl_failure_leaves_no_mapping_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(_: Path) -> None:
        raise RuntimeError("ACL rejected")

    monkeypatch.setattr("lab.network_validation.phase1_runtime._restrict_windows_acl", reject)
    store = MappingStore(tmp_path, PACKAGE["package_id"], PACKAGE["canonical_digest"], bytes(range(32)))
    with pytest.raises(RuntimeError):
        store.ensure(str(_first_unit()["execution_token"]), created_at="2026-01-01T00:00:00Z")
    assert not store.path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_marker_flows_are_excluded_only_from_temporary_model_input(tmp_path: Path) -> None:
    staging = tmp_path / "attempt.staging"
    zeek = staging / "zeek"
    runtime = staging / ".runtime"
    zeek.mkdir(parents=True)
    runtime.mkdir()
    conn_rows = [{"uid": "marker", "proto": "tcp"}, {"uid": "scenario", "proto": "tcp"}]
    http_rows = [
        {"uid": "marker", "uri": "/sensor-marker/start/abc"},
        {"uid": "scenario", "uri": "/scenario"},
    ]
    for name, rows in (("conn.log", conn_rows), ("http.log", http_rows), ("dns.log", [])):
        (zeek / name).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    runner = object.__new__(Phase1DockerRunner)
    runner.contract = validate_runtime_contract()
    paths = SessionPaths(tmp_path, staging, tmp_path / "sealed", tmp_path / "failed")
    filtered = runner._prepare_model_input_zeek(paths)
    filtered_conn = [json.loads(line) for line in (filtered / "conn.log").read_text(encoding="utf-8").splitlines()]
    assert [row["uid"] for row in filtered_conn] == ["scenario"]
    assert len((zeek / "conn.log").read_text(encoding="utf-8").splitlines()) == 2


def test_marker_filter_rejects_shared_marker_and_scenario_uid(tmp_path: Path) -> None:
    staging = tmp_path / "attempt.staging"
    zeek = staging / "zeek"
    (staging / ".runtime").mkdir(parents=True)
    zeek.mkdir()
    (zeek / "conn.log").write_text('{"uid":"shared"}\n', encoding="utf-8")
    (zeek / "http.log").write_text(
        '{"uid":"shared","uri":"/sensor-marker/start/abc"}\n{"uid":"shared","uri":"/scenario"}\n',
        encoding="utf-8",
    )
    (zeek / "dns.log").write_bytes(b"")
    runner = object.__new__(Phase1DockerRunner)
    runner.contract = validate_runtime_contract()
    paths = SessionPaths(tmp_path, staging, tmp_path / "sealed", tmp_path / "failed")
    with pytest.raises(TechnicalFailure):
        runner._prepare_model_input_zeek(paths)


def test_runtime_package_preserves_scientific_inputs_and_binds_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lab.network_validation.runtime_execution_package.validate_runtime_sources_commit", lambda _: None)
    value = build_payload("a" * 40, "2026-01-01T00:00:00Z")
    assert validate_package(value) == value
    assert value["scientific_protocol_changed"] is False
    assert value["operational_runtime_contract_complete"] is True
    assert value["canonical_phase1_runner_available"] is True
    assert value["phase1_runtime_contract_digest"] == runtime_contract_digest()
    assert value["supersedes_package_id"] != value["package_id"]
    predecessor = load_json(OFFICIAL_PACKAGE_V2_PATH)
    assert all(value[field] == predecessor[field] for field in SCIENTIFIC_DIGEST_FIELDS)
    with pytest.raises(ContractError):
        validate_package(dict(value, execution_session_count=863))


def test_runtime_package_preview_and_official_write_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preview = build_preview()
    assert preview["official_runtime_execution_package_created"] is False
    assert "runtime_sources_not_committed" in preview["blockers"]
    monkeypatch.setattr("lab.network_validation.runtime_execution_package.validate_runtime_sources_commit", lambda _: None)
    target = tmp_path / "official-v3.json"
    with pytest.raises(ContractError):
        write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", False)
    write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", True)
    with pytest.raises(ContractError):
        write_official_package(target, "a" * 40, "2026-01-01T00:00:00Z", True)


def test_run_command_requires_exact_token_and_explicit_one_unit_confirmation() -> None:
    parsed = parser().parse_args([
        "run-one-phase1-session",
        "--output-root", "G:/output",
        "--secret-root", "G:/secret",
        "--expected-secret-fingerprint", "a" * 64,
        "--confirm-execution-token", "b" * 24,
    ])
    assert parsed.confirm_one_unit is False
    assert parsed.confirm_execution_token == "b" * 24


def test_runtime_roots_must_be_external_separate_and_package_bound(tmp_path: Path) -> None:
    runner = object.__new__(Phase1DockerRunner)
    runner.package = PACKAGE
    runner.output_root = (tmp_path / "output" / PACKAGE["package_id"]).resolve()
    runner.secret_root = (tmp_path / "secret" / PACKAGE["package_id"]).resolve()
    runner._validate_campaign_roots()
    runner.secret_root = runner.output_root
    with pytest.raises(ContractError):
        runner._validate_campaign_roots()


def test_sealed_completion_recovery_validates_without_rerunning_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / PACKAGE["package_id"]
    ledger_path = output_root / "control" / "campaign-ledger.jsonl"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_bytes(b"")
    ledger = LedgerStore(ledger_path, PACKAGE["package_id"], PACKAGE["canonical_digest"])
    unit = _first_unit()
    identity = session_identity(PACKAGE, unit, 1)
    ledger.append(identity, "session_started", occurred_at="2026-01-01T00:00:00Z")
    paths = SessionPaths(
        output_root / "sessions" / identity.session_token,
        output_root / "sessions" / identity.session_token / ".attempt-01.staging",
        output_root / "sessions" / identity.session_token / "attempt-01",
        output_root / "sessions" / identity.session_token / "attempt-01.failed",
    )
    paths.sealed.mkdir(parents=True)
    contract = validate_runtime_contract()
    for relative in contract["artifact_schemas"]:
        target = paths.sealed / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"{}\n")
    evaluation = "e" * 64
    feature_row = {
        "schema_version": "network_validation_phase1_feature_row_v1",
        "evaluation_token": evaluation,
        "feature_contract_digest": PACKAGE["feature_contract_digest"],
        "feature_order_digest": PACKAGE["feature_order_digest"],
        "feature_row": [0.0] * 51,
    }
    (paths.sealed / "feature_rows.jsonl").write_text(json.dumps(feature_row) + "\n", encoding="utf-8")
    runner = object.__new__(Phase1DockerRunner)
    runner.package = PACKAGE
    runner.output_root = output_root
    runner.contract = contract
    runner.ledger = ledger
    runner.mapping = type("Mapping", (), {"read": lambda self: [{"execution_token": unit["execution_token"], "evaluation_token": evaluation}]})()
    runner._image_inventory = dict
    monkeypatch.setattr(
        "lab.network_validation.phase1_docker_runner.validate_session_integrity_manifest",
        lambda *args: {},
    )
    result = runner.recover_sealed_completion(identity.attempt_id)
    assert result["scientific_behavior_rerun"] is False
    assert result["containers_started"] is False
    assert ledger.read()[-1]["event_type"] == "session_completed"
