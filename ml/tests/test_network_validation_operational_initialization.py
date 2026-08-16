from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lab.network_validation.contracts import ContractError
from lab.network_validation.operational_initialization import (
    GENESIS_DIGEST,
    atomic_install_files,
    audit_initialization_contracts,
    build_initialization_manifest,
    encode_ledger_record,
    evaluation_token,
    generate_mapping_secret,
    ledger_record_digest,
    mapping_secret_fingerprint,
    validate_acl_description,
    validate_initialization_manifest,
    validate_ledger_bytes,
    validate_secret_storage_path,
)


PACKAGE = {
    "package_id": "network-validation-execution-" + "a" * 16,
    "canonical_digest": "a" * 64,
    "superseding_freeze_id": "network-validation-superseding-freeze-" + "b" * 16,
    "superseding_freeze_digest": "b" * 64,
    "run_plan_digest": "c" * 64,
    "exact_execution_order_digest": "d" * 64,
    "ledger_contract_digest": "e" * 64,
    "sealed_mapping_contract_digest": "f" * 64,
    "initialization_contract_digest": "1" * 64,
    "output_contract_digest": "2" * 64,
}


def _record(sequence: int, previous: str, event_type: str = "session_started") -> dict[str, object]:
    value: dict[str, object] = {
        "record_sequence": sequence,
        "attempt_id": f"attempt-{sequence}",
        "event_type": event_type,
        "previous_record_digest": previous,
        "package_id": PACKAGE["package_id"],
        "package_canonical_digest": PACKAGE["canonical_digest"],
        "scenario_token": "scenario-001",
        "session_token": "session-001",
        "status": "started",
    }
    value["record_digest"] = ledger_record_digest(value)
    return value


def test_operational_contract_audit_is_complete_and_non_executing() -> None:
    result = audit_initialization_contracts()
    assert result["operational_initialization_contract_complete"] is True
    assert result["scientific_protocol_changed"] is False
    assert result["mapping_secret_created"] is False
    assert result["campaign_ledger_created"] is False
    assert result["scientific_campaign_started"] is False
    assert all(len(result[key]) == 64 for key in result if key.endswith("_digest"))


def test_mapping_secret_bytes_fingerprint_and_token_contract() -> None:
    secret = generate_mapping_secret()
    assert type(secret) is bytes
    assert len(secret) == 32
    assert mapping_secret_fingerprint(secret) == hashlib.sha256(secret).hexdigest()
    token = evaluation_token(secret, "exact-token")
    assert len(token) == 64 and token == token.lower()
    assert token == evaluation_token(secret, "exact-token")
    assert token != evaluation_token(secret, "exact-token\n")
    assert token != evaluation_token(bytes(reversed(secret)), "exact-token")
    assert set(token) <= set("0123456789abcdef")
    report = audit_initialization_contracts()
    assert secret.hex() not in str(report)


def test_secret_storage_and_acl_fail_closed(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    output = tmp_path / "output"
    external = tmp_path / "secrets" / "mapping-secret.bin"
    assert validate_secret_storage_path(external, repository, output) == external.resolve()
    with pytest.raises(ContractError):
        validate_secret_storage_path(repository / "mapping-secret.bin", repository, output)
    with pytest.raises(ContractError):
        validate_secret_storage_path(output / "mapping-secret.bin", repository, output)
    validate_acl_description(False, {"operator": "FullControl", "SYSTEM": "FullControl"}, "operator")
    with pytest.raises(ContractError):
        validate_acl_description(False, {"operator": "FullControl", "Everyone": "Read"}, "operator")
    with pytest.raises(ContractError):
        validate_acl_description(True, {"operator": "FullControl"}, "operator")


def test_initialization_manifest_is_bound_and_zero_attempt() -> None:
    fingerprint = "3" * 64
    value = build_initialization_manifest(PACKAGE, fingerprint, "2026-01-01T00:00:00Z")
    assert validate_initialization_manifest(value, PACKAGE, fingerprint) == value
    assert value["campaign_initialized"] is True
    assert value["scientific_campaign_started"] is False
    assert value["attempt_count"] == value["scientific_sessions_executed"] == 0
    assert value["mapping_entries"] == 0
    for field in (
        "package_canonical_digest",
        "mapping_secret_fingerprint",
        "run_plan_digest",
        "campaign_ledger_contract_digest",
        "campaign_initialization_contract_digest",
    ):
        tampered = dict(value, **{field: "9" * 64})
        with pytest.raises(ContractError):
            validate_initialization_manifest(tampered, PACKAGE, fingerprint)


def test_zero_byte_and_chained_ledger_validation() -> None:
    assert validate_ledger_bytes(b"", PACKAGE["package_id"], PACKAGE["canonical_digest"], expected_record_count=0) == []
    first = _record(1, GENESIS_DIGEST)
    second = _record(2, str(first["record_digest"]), "session_completed")
    content = encode_ledger_record(first) + encode_ledger_record(second)
    assert validate_ledger_bytes(content, PACKAGE["package_id"], PACKAGE["canonical_digest"], expected_record_count=2) == [first, second]
    with pytest.raises(ContractError):
        validate_ledger_bytes(content[:-1], PACKAGE["package_id"], PACKAGE["canonical_digest"])
    with pytest.raises(ContractError):
        validate_ledger_bytes(b"\xef\xbb\xbf" + content, PACKAGE["package_id"], PACKAGE["canonical_digest"])
    with pytest.raises(ContractError):
        validate_ledger_bytes(content.replace(b"\n", b"\r\n"), PACKAGE["package_id"], PACKAGE["canonical_digest"])


def test_ledger_rejects_tamper_chain_sequence_binding_and_init_event() -> None:
    first = _record(1, GENESIS_DIGEST)
    bad_cases = []
    for updates in (
        {"record_sequence": 2},
        {"previous_record_digest": "9" * 64},
        {"package_id": "wrong"},
        {"package_canonical_digest": "9" * 64},
        {"event_type": "initialization"},
    ):
        value = dict(first, **updates)
        value["record_digest"] = ledger_record_digest(value)
        bad_cases.append(encode_ledger_record(value))
    tampered = encode_ledger_record(first).replace(b'"status":"started"', b'"status":"stopped"')
    bad_cases.append(tampered)
    for content in bad_cases:
        with pytest.raises(ContractError):
            validate_ledger_bytes(content, PACKAGE["package_id"], PACKAGE["canonical_digest"])
    second = _record(2, str(first["record_digest"]), "session_completed")
    reordered = encode_ledger_record(second) + encode_ledger_record(first)
    duplicate = encode_ledger_record(first) + encode_ledger_record(first)
    for content in (reordered, duplicate):
        with pytest.raises(ContractError):
            validate_ledger_bytes(content, PACKAGE["package_id"], PACKAGE["canonical_digest"])
    with pytest.raises(ContractError):
        validate_ledger_bytes(encode_ledger_record(first), PACKAGE["package_id"], PACKAGE["canonical_digest"], expected_record_count=2)


def test_atomic_install_rolls_back_only_current_attempt_files(tmp_path: Path) -> None:
    preexisting = tmp_path / "preexisting.txt"
    preexisting.write_text("preserve", encoding="utf-8")
    for failure in range(1, 5):
        root = tmp_path / f"attempt-{failure}"
        files = {root / f"file-{index}": f"value-{index}".encode() for index in range(1, 5)}
        with pytest.raises(RuntimeError):
            atomic_install_files(files, validate_temporary=lambda _: None, fail_after_install=failure)
        assert not any(path.exists() for path in files)
        assert not list(root.glob("*.tmp"))
        assert preexisting.read_text(encoding="utf-8") == "preserve"


def test_atomic_install_rolls_back_preparation_and_validation_failures(tmp_path: Path) -> None:
    files = {tmp_path / f"prepared-{index}": b"value" for index in range(1, 6)}
    for failure in range(1, 6):
        with pytest.raises(RuntimeError):
            atomic_install_files(files, validate_temporary=lambda _: None, fail_after_prepare=failure)
        assert not any(path.exists() for path in files)
    with pytest.raises(RuntimeError):
        atomic_install_files(files, validate_temporary=lambda _: (_ for _ in ()).throw(RuntimeError("mock ACL validation failure")))
    assert not any(path.exists() for path in files)


def test_atomic_install_success_and_overwrite_rejection(tmp_path: Path) -> None:
    files = {tmp_path / "a": b"a", tmp_path / "b": b"b"}
    atomic_install_files(files, validate_temporary=lambda temporary: [path.read_bytes() for path in temporary.values()])
    assert [path.read_bytes() for path in files] == [b"a", b"b"]
    with pytest.raises(ContractError):
        atomic_install_files(files, validate_temporary=lambda _: None)
