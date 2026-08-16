from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from .contracts import ContractError, canonical_bytes, digest, load_json


EXECUTION = Path(__file__).with_name("execution")
MAPPING_CONTRACT_PATH = EXECUTION / "sealed_mapping_contract_v2.json"
LEDGER_CONTRACT_PATH = EXECUTION / "campaign_ledger_contract_v2.json"
INITIALIZATION_CONTRACT_PATH = EXECUTION / "campaign_initialization_contract.json"

MAPPING_SCHEMA = "network_validation_sealed_mapping_contract_v2"
LEDGER_SCHEMA = "network_validation_campaign_ledger_contract_v2"
INITIALIZATION_SCHEMA = "network_validation_campaign_initialization_contract_v1"
INITIALIZATION_MANIFEST_SCHEMA = "network_validation_campaign_initialization_manifest_v1"
SECRET_METADATA_SCHEMA = "network_validation_mapping_secret_metadata_v1"
GENESIS_DIGEST = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate_mapping_contract(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or load_json(MAPPING_CONTRACT_PATH)
    _require(value.get("schema_version") == MAPPING_SCHEMA, "mapping contract schema mismatch")
    _require(value.get("supersedes_contract_digest") == "4a4c4b35a1356848e8c60425b70def4631dbd31ac7a492e8dfe40fd7bb3d9a5e", "mapping predecessor mismatch")
    _require(value.get("mapping_algorithm") == "HMAC-SHA256", "mapping algorithm mismatch")
    source = value.get("mapping_input", {})
    _require(source == {
        "field": "execution_token",
        "source": "phase1_run_plan.json",
        "encoding": "UTF-8",
        "bom": False,
        "trailing_newline": False,
        "unicode_transformation": "none",
    }, "mapping input semantics mismatch")
    key = value.get("mapping_key", {})
    _require(key.get("key_size_bytes") == 32 and key.get("key_size_bits") == 256, "mapping key size mismatch")
    _require(key.get("generation") == "cryptographically_secure_random" and key.get("randomness_source") == "OS_CSPRNG", "mapping key generation mismatch")
    _require(key.get("serialization") == "raw_binary" and key.get("serialized_length_bytes") == 32, "mapping key serialization mismatch")
    _require(key.get("newline") == "none" and key.get("text_encoding") == "not_applicable", "mapping key encoding mismatch")
    _require(key.get("logical_filename") == "mapping-secret.bin", "mapping secret filename mismatch")
    fingerprint = value.get("fingerprint", {})
    _require(fingerprint == {
        "algorithm": "SHA-256",
        "input": "raw_32_secret_bytes",
        "encoding": "lowercase_hexadecimal",
        "length_characters": 64,
        "secret": False,
    }, "mapping fingerprint mismatch")
    token = value.get("evaluation_token", {})
    _require(token.get("algorithm") == "HMAC-SHA256", "evaluation token algorithm mismatch")
    _require(token.get("key") == "raw_secret_bytes" and token.get("message") == "UTF8_exact_execution_token", "evaluation token inputs mismatch")
    _require(token.get("encoding") == "lowercase_hexadecimal" and token.get("length_characters") == 64, "evaluation token representation mismatch")
    _require(token.get("truncated") is False and token.get("salt") == "none" and token.get("package_digest_in_message") is False, "evaluation token transformation mismatch")
    storage = value.get("secret_storage", {})
    _require(storage.get("storage_class") == "external_secret_root", "secret storage class mismatch")
    _require(storage.get("repository_storage") == "forbidden" and storage.get("scientific_output_root_storage") == "forbidden", "unsafe secret storage policy")
    overwrite = value.get("overwrite_policy", {})
    _require(overwrite.get("overwrite_existing_secret") is False and overwrite.get("regenerate_existing_secret") is False, "secret overwrite policy mismatch")
    _require(value.get("mapping_created_at_initialization") is False and value.get("mapping_entries_at_initialization") == 0, "mapping initialization state mismatch")
    canonical_bytes(value)
    return value


def validate_ledger_contract(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or load_json(LEDGER_CONTRACT_PATH)
    _require(value.get("schema_version") == LEDGER_SCHEMA, "ledger contract schema mismatch")
    _require(value.get("supersedes_contract_digest") == "237aa3302771ff97da6fef075983f4440360bf63c3040fd0ada74e55efd7d3e9", "ledger predecessor mismatch")
    _require(value.get("relative_path") == "control/campaign-ledger.jsonl", "ledger path mismatch")
    physical = value.get("physical_format", {})
    _require(physical == {"format": "JSON Lines", "encoding": "UTF-8", "bom": "forbidden", "line_ending": "LF", "append_only": True}, "ledger physical format mismatch")
    initial = value.get("initial_state", {})
    _require(initial.get("file_exists") is True and initial.get("file_size_bytes") == 0 and initial.get("record_count") == 0, "ledger empty state mismatch")
    _require(initial.get("attempt_record_count") == 0 and initial.get("scientific_session_record_count") == 0, "ledger initial counts mismatch")
    _require(initial.get("initialization_is_ledger_event") is False, "initialization must not be a ledger event")
    _require(value.get("genesis_previous_record_digest") == GENESIS_DIGEST, "ledger genesis mismatch")
    sequence = value.get("sequence", {})
    _require(sequence.get("field") == "record_sequence" and sequence.get("first") == 1 and sequence.get("increment") == 1, "ledger sequence mismatch")
    required = set(value.get("required_record_fields", []))
    _require({"record_sequence", "package_id", "package_canonical_digest", "previous_record_digest", "record_digest"} <= required, "ledger binding fields missing")
    _require(value.get("package_binding_fields") == ["package_id", "package_canonical_digest"], "ledger package binding mismatch")
    start = value.get("scientific_campaign_start", {})
    _require(start.get("event_type") == "session_started", "scientific campaign start event mismatch")
    _require(start.get("planned_is_start") is False and start.get("initialization_is_start") is False and start.get("preflight_is_start") is False, "scientific campaign start semantics mismatch")
    _require("session_started" in value.get("permitted_event_types", []), "session_started event not permitted")
    canonical_bytes(value)
    return value


def validate_initialization_contract(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or load_json(INITIALIZATION_CONTRACT_PATH)
    _require(value.get("schema_version") == INITIALIZATION_SCHEMA, "initialization contract schema mismatch")
    _require(value.get("scope") == "operational_initialization_only" and value.get("scientific_protocol_changed") is False, "initialization scope mismatch")
    files = value.get("output_control_files", {})
    _require(files == {"initialization_manifest": "control/campaign-initialization.json", "campaign_ledger": "control/campaign-ledger.jsonl"}, "initialization output paths mismatch")
    manifest = value.get("initialization_manifest", {})
    _require(manifest.get("schema_version") == INITIALIZATION_MANIFEST_SCHEMA, "initialization manifest schema mismatch")
    _require(manifest.get("initialization_state") == "initialized_not_started", "initialization state mismatch")
    _require(manifest.get("canonicalization") == "repository_canonical_json", "initialization canonicalization mismatch")
    _require(manifest.get("self_digest_excluded_fields") == ["canonical_payload_sha256"], "initialization self digest convention mismatch")
    expected_initial = {
        "campaign_initialized": True,
        "scientific_campaign_started": False,
        "attempt_count": 0,
        "scientific_sessions_executed": 0,
        "mapping_entries": 0,
        "labels_created": False,
        "labels_unlocked": False,
    }
    _require(manifest.get("initial_values") == expected_initial, "initialization zero-attempt state mismatch")
    atomic = value.get("atomic_installation", {})
    _require(atomic.get("fail_closed") is True and atomic.get("ordered_stages", [])[-1:] == ["post_validate_complete_state"], "initialization atomicity mismatch")
    rollback = value.get("rollback", {})
    _require(rollback.get("scope") == "files_created_by_current_initialization_attempt_only" and rollback.get("preexisting_files_must_not_be_deleted") is True, "initialization rollback mismatch")
    idempotence = value.get("idempotence", {})
    _require(idempotence.get("status") == "CAMPAIGN_ALREADY_INITIALIZED", "initialization idempotence status mismatch")
    _require(idempotence.get("regenerate_secret") is False and idempotence.get("truncate_ledger") is False and idempotence.get("change_initialized_at") is False, "initialization idempotence mismatch")
    _require(value.get("scientific_campaign_start", {}).get("ledger_event_type") == "session_started", "initialization campaign start mismatch")
    canonical_bytes(value)
    return value


def audit_initialization_contracts() -> dict[str, Any]:
    mapping = validate_mapping_contract()
    ledger = validate_ledger_contract()
    initialization = validate_initialization_contract()
    return {
        "operational_initialization_contract_complete": True,
        "scientific_protocol_changed": False,
        "sealed_mapping_contract_digest": digest(mapping),
        "ledger_contract_digest": digest(ledger),
        "initialization_contract_digest": digest(initialization),
        "mapping_secret_created": False,
        "campaign_ledger_created": False,
        "scientific_campaign_started": False,
    }


def generate_mapping_secret() -> bytes:
    return secrets.token_bytes(32)


def mapping_secret_fingerprint(secret: bytes) -> str:
    _require(isinstance(secret, bytes) and len(secret) == 32, "mapping secret must be exactly 32 raw bytes")
    return hashlib.sha256(secret).hexdigest()


def evaluation_token(secret: bytes, execution_token: str) -> str:
    mapping_secret_fingerprint(secret)
    _require(isinstance(execution_token, str), "execution token must be a string")
    return hmac.new(secret, execution_token.encode("utf-8"), hashlib.sha256).hexdigest()


def validate_secret_storage_path(secret_path: Path, repository_root: Path, scientific_output_root: Path) -> Path:
    resolved = secret_path.resolve(strict=False)
    repository = repository_root.resolve(strict=False)
    output = scientific_output_root.resolve(strict=False)
    _require(resolved.name == "mapping-secret.bin", "mapping secret filename mismatch")
    _require(not resolved.is_relative_to(repository), "tracked repository secret storage rejected")
    _require(not resolved.is_relative_to(output), "scientific output root secret storage rejected")
    return resolved


def validate_acl_description(inheritance_enabled: bool, principal_rights: Mapping[str, str], current_operator: str) -> None:
    _require(inheritance_enabled is False, "secret ACL inheritance must be disabled")
    normalized = {name.casefold(): rights for name, rights in principal_rights.items()}
    forbidden = {"everyone", "users", "builtin\\users", "authenticated users", "nt authority\\authenticated users"}
    _require(not (set(normalized) & forbidden), "broad secret ACL principal rejected")
    allowed = {current_operator.casefold(), "system", "nt authority\\system", "builtin\\administrators"}
    _require(set(normalized) <= allowed, "unexpected secret ACL principal")
    _require(current_operator.casefold() in normalized, "campaign operator ACL missing")
    _require(all(rights == "FullControl" for rights in normalized.values()), "secret ACL rights mismatch")


def build_secret_metadata(package_id: str, package_digest: str, secret: bytes, created_at: str) -> dict[str, Any]:
    fingerprint = mapping_secret_fingerprint(secret)
    _require(HEX64.fullmatch(package_digest) is not None, "invalid package digest")
    return {
        "schema_version": SECRET_METADATA_SCHEMA,
        "package_id": package_id,
        "package_canonical_digest": package_digest,
        "mapping_algorithm": "HMAC-SHA256",
        "key_size_bytes": 32,
        "secret_filename": "mapping-secret.bin",
        "secret_fingerprint": fingerprint,
        "fingerprint_algorithm": "SHA-256",
        "created_at": created_at,
    }


def _self_digest(value: dict[str, Any], field: str = "canonical_payload_sha256") -> str:
    return digest({key: item for key, item in value.items() if key != field})


def build_initialization_manifest(package: dict[str, Any], mapping_fingerprint: str, initialized_at: str) -> dict[str, Any]:
    _require(HEX64.fullmatch(mapping_fingerprint) is not None, "invalid mapping secret fingerprint")
    value = {
        "schema_version": INITIALIZATION_MANIFEST_SCHEMA,
        "initialization_state": "initialized_not_started",
        "package_id": package["package_id"],
        "package_canonical_digest": package["canonical_digest"],
        "superseding_freeze_id": package["superseding_freeze_id"],
        "superseding_freeze_canonical_digest": package["superseding_freeze_digest"],
        "run_plan_digest": package["run_plan_digest"],
        "exact_execution_order_digest": package["exact_execution_order_digest"],
        "campaign_ledger_contract_digest": package["ledger_contract_digest"],
        "sealed_mapping_contract_digest": package["sealed_mapping_contract_digest"],
        "campaign_initialization_contract_digest": package["initialization_contract_digest"],
        "output_contract_digest": package["output_contract_digest"],
        "mapping_secret_fingerprint": mapping_fingerprint,
        "mapping_algorithm": "HMAC-SHA256",
        "campaign_initialized": True,
        "scientific_campaign_started": False,
        "attempt_count": 0,
        "scientific_sessions_executed": 0,
        "mapping_entries": 0,
        "labels_created": False,
        "labels_unlocked": False,
        "initialized_at": initialized_at,
    }
    value["canonical_payload_sha256"] = _self_digest(value)
    return value


def validate_initialization_manifest(value: dict[str, Any], package: dict[str, Any], mapping_fingerprint: str) -> dict[str, Any]:
    contract = validate_initialization_contract()
    required = set(contract["initialization_manifest"]["required_fields"])
    _require(set(value) == required, "initialization manifest fields mismatch")
    _require(value.get("schema_version") == INITIALIZATION_MANIFEST_SCHEMA, "initialization manifest schema mismatch")
    _require(value.get("initialization_state") == "initialized_not_started", "initialization manifest state mismatch")
    bindings = {
        "package_id": package["package_id"],
        "package_canonical_digest": package["canonical_digest"],
        "superseding_freeze_id": package["superseding_freeze_id"],
        "superseding_freeze_canonical_digest": package["superseding_freeze_digest"],
        "run_plan_digest": package["run_plan_digest"],
        "exact_execution_order_digest": package["exact_execution_order_digest"],
        "campaign_ledger_contract_digest": package["ledger_contract_digest"],
        "sealed_mapping_contract_digest": package["sealed_mapping_contract_digest"],
        "campaign_initialization_contract_digest": package["initialization_contract_digest"],
        "output_contract_digest": package["output_contract_digest"],
        "mapping_secret_fingerprint": mapping_fingerprint,
        "mapping_algorithm": "HMAC-SHA256",
    }
    _require(all(value.get(key) == expected for key, expected in bindings.items()), "initialization manifest binding mismatch")
    for key, expected in contract["initialization_manifest"]["initial_values"].items():
        _require(value.get(key) == expected, "initialization manifest zero-attempt state mismatch")
    _require(value.get("canonical_payload_sha256") == _self_digest(value), "initialization manifest digest mismatch")
    canonical_bytes(value)
    return value


def ledger_record_digest(record: dict[str, Any]) -> str:
    return digest({key: item for key, item in record.items() if key != "record_digest"})


def encode_ledger_record(record: dict[str, Any]) -> bytes:
    _require(record.get("record_digest") == ledger_record_digest(record), "ledger record digest mismatch")
    return canonical_bytes(record) + b"\n"


def validate_ledger_bytes(
    content: bytes,
    package_id: str,
    package_digest: str,
    *,
    expected_record_count: int | None = None,
    expected_last_digest: str | None = None,
) -> list[dict[str, Any]]:
    contract = validate_ledger_contract()
    _require(not content.startswith(b"\xef\xbb\xbf"), "ledger BOM forbidden")
    _require(b"\r" not in content, "ledger line ending must be LF")
    if not content:
        _require(expected_record_count in (None, 0), "ledger truncation detected")
        _require(expected_last_digest in (None, GENESIS_DIGEST), "ledger last digest mismatch")
        return []
    _require(content.endswith(b"\n"), "ledger final line is truncated")
    records: list[dict[str, Any]] = []
    previous = GENESIS_DIGEST
    required = set(contract["required_record_fields"])
    for sequence, raw in enumerate(content.splitlines(), start=1):
        try:
            record = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError("invalid ledger JSONL") from error
        _require(isinstance(record, dict), "ledger record must be an object")
        _require(required <= set(record), "ledger record fields missing")
        _require(record.get("record_sequence") == sequence, "ledger sequence gap or duplicate")
        _require(record.get("package_id") == package_id and record.get("package_canonical_digest") == package_digest, "ledger package binding mismatch")
        _require(record.get("event_type") in contract["permitted_event_types"], "ledger event type rejected")
        _require(record.get("previous_record_digest") == previous, "ledger chain break")
        actual = ledger_record_digest(record)
        _require(record.get("record_digest") == actual, "ledger record digest mismatch")
        _require(raw == canonical_bytes(record), "ledger record is not canonical JSON")
        previous = actual
        records.append(record)
    if expected_record_count is not None:
        _require(len(records) == expected_record_count, "ledger truncation detected")
    if expected_last_digest is not None:
        _require(previous == expected_last_digest, "ledger last digest mismatch")
    return records


def atomic_install_files(
    files: Mapping[Path, bytes],
    *,
    validate_temporary: Callable[[Mapping[Path, Path]], None],
    fail_after_prepare: int | None = None,
    fail_after_install: int | None = None,
) -> None:
    _require(bool(files), "atomic installation requires files")
    targets = list(files)
    _require(len(set(targets)) == len(targets), "duplicate atomic installation target")
    _require(all(not path.exists() for path in targets), "atomic installation target already exists")
    temporary: dict[Path, Path] = {}
    installed: list[Path] = []
    try:
        for index, (target, content) in enumerate(files.items(), start=1):
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
            with temp.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary[target] = temp
            if fail_after_prepare == index:
                raise RuntimeError("simulated atomic preparation failure")
        validate_temporary(temporary)
        for index, target in enumerate(targets, start=1):
            temporary[target].replace(target)
            installed.append(target)
            if fail_after_install == index:
                raise RuntimeError("simulated atomic installation failure")
    except Exception:
        for target in reversed(installed):
            if target.exists():
                target.unlink()
        for temp in temporary.values():
            if temp.exists():
                temp.unlink()
        raise
