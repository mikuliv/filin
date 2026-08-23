from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import ContractError, canonical_bytes, digest, load_json
from .operational_initialization import (
    evaluation_token,
    ledger_record_digest,
    mapping_secret_fingerprint,
    validate_initialization_manifest,
    validate_ledger_bytes,
)
from .phase1_execution_package import RUN_PLAN_PATH, validate_run_plan

EXECUTION = Path(__file__).with_name("execution")
RUNTIME_CONTRACT_PATH = EXECUTION / "phase1_runtime_contract.json"
RUNTIME_SCHEMA = "network_validation_phase1_runtime_contract_v1"
MAPPING_ENTRY_SCHEMA = "network_validation_sealed_mapping_entry_v1"
FEATURE_ROW_SCHEMA = "network_validation_phase1_feature_row_v1"
SESSION_MANIFEST_SCHEMA = "network_validation_phase1_session_integrity_manifest_v1"
HEX24 = re.compile(r"^[0-9a-f]{24}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UTC_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_runtime_contract(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or load_json(RUNTIME_CONTRACT_PATH)
    _require(value.get("schema_version") == RUNTIME_SCHEMA, "runtime contract schema mismatch")
    _require(value.get("scope") == "operational_phase1_execution", "runtime contract scope mismatch")
    _require(value.get("scientific_protocol_changed") is False, "runtime contract changes scientific protocol")
    extensions = value.get("extends_contracts", {})
    expected_extensions = {
        "sealed_mapping_contract_digest": digest(load_json(EXECUTION / "sealed_mapping_contract_v2.json")),
        "campaign_ledger_contract_digest": digest(load_json(EXECUTION / "campaign_ledger_contract_v2.json")),
        "runner_contract_digest": digest(load_json(EXECUTION / "runner_contract.json")),
        "output_contract_digest": digest(load_json(EXECUTION / "output_contract.json")),
        "session_integrity_contract_digest": digest(load_json(EXECUTION / "session_integrity_contract.json")),
        "preflight_contract_digest": digest(load_json(EXECUTION / "phase1_preflight_contract.json")),
    }
    _require(extensions == expected_extensions, "runtime contract extension digest mismatch")
    identity = value.get("identity_derivation", {})
    _require(identity.get("attempt_number") == {
        "first": 1,
        "maximum": 2,
        "derive_from": "count_session_started_records_for_execution_token_plus_one",
    }, "attempt number contract mismatch")
    record = value.get("ledger_record_profile", {})
    exact_fields = set(record.get("exact_fields", []))
    required_fields = set(load_json(EXECUTION / "campaign_ledger_contract_v2.json")["required_record_fields"])
    _require(required_fields <= exact_fields, "runtime ledger profile omits base fields")
    _require({"attempt_number", "execution_token", "reason_code", "occurred_at"} <= exact_fields, "runtime ledger identity fields missing")
    machine = value.get("ledger_state_machine", {})
    _require(machine.get("initial") == "not_started", "ledger state machine initial state mismatch")
    _require(machine.get("transitions") == {
        "not_started:session_started:1": "attempt_1_active",
        "attempt_1_active:session_completed:1": "completed",
        "attempt_1_active:session_failed:1": "attempt_1_failed",
        "attempt_1_failed:retry_requested:1": "retry_authorized",
        "retry_authorized:session_started:2": "attempt_2_active",
        "attempt_2_active:session_completed:2": "completed",
        "attempt_2_active:session_failed:2": "terminal_failed",
    }, "ledger state machine transition mismatch")
    roots = value.get("campaign_roots", {})
    _require(roots.get("repository_storage_forbidden") is True, "runtime roots may not use repository storage")
    _require(roots.get("output_root_leaf") == "{package_id}" and roots.get("secret_root_leaf") == "{package_id}", "runtime root identity mismatch")
    _require(roots.get("roots_must_be_distinct_and_non_nested") is True, "runtime root separation missing")
    mapping = value.get("mapping_lifecycle", {})
    _require(mapping.get("relative_path") == "sealed-mapping.jsonl", "mapping path mismatch")
    _require(mapping.get("create_after") == "session_started_ledger_record_committed", "mapping lifecycle start mismatch")
    _require(mapping.get("create_before") == "scientific_behavior_launch", "mapping lifecycle end mismatch")
    _require(mapping.get("entries_per_execution_token") == 1 and mapping.get("retry_reuses_entry") is True, "mapping cardinality mismatch")
    model_filter = value.get("model_input_filter", {})
    _require(model_filter.get("raw_zeek_outputs_immutable") is True, "raw Zeek mutation is forbidden")
    _require(model_filter.get("marker_http_uri_prefix") == "/sensor-marker/", "marker filter identity mismatch")
    _require(model_filter.get("excluded_conn_rows") == "uid_referenced_by_excluded_http_rows", "marker connection filter mismatch")
    _require(model_filter.get("marker_metadata_in_feature_row") is False, "marker metadata feature leakage")
    evaluator = value.get("evaluator_boundary", {})
    _require(evaluator.get("session_output_root_access") == "runner_only_before_label_unlock", "evaluator session access boundary missing")
    _require(evaluator.get("evaluator_input") == "detached_feature_rows_keyed_only_by_evaluation_token", "evaluator projection mismatch")
    _require(evaluator.get("path_and_filename_metadata_visible_to_evaluator") is False, "evaluator path metadata leakage")
    layout = value.get("session_output_layout", {})
    _require(layout.get("attempt_staging") and layout.get("attempt_sealed") and layout.get("failed_attempt"), "session layout incomplete")
    schemas = value.get("artifact_schemas", {})
    required_outputs = {row["name"] for row in load_json(EXECUTION / "output_contract.json")["required_session_outputs"]}
    _require(set(schemas) == required_outputs, "runtime artifact schema coverage mismatch")
    feature = schemas["feature_rows.jsonl"]
    _require(feature.get("row_count") == 1 and feature.get("feature_count") == 51, "feature row cardinality mismatch")
    _require(feature.get("forbidden_runner_metadata") is True, "feature row metadata guard missing")
    _require(value.get("stop_gate", {}).get("maximum_completed_units_per_invocation") == 1, "unit stop gate mismatch")
    recovery = value.get("completion_recovery", {})
    _require(recovery.get("requires_exact_attempt_id_confirmation") is True, "completion recovery confirmation missing")
    _require(recovery.get("requires_full_output_digest_and_schema_validation") is True, "completion recovery validation missing")
    _require(recovery.get("scientific_behavior_rerun") is False, "completion recovery may not rerun behavior")
    canonical_bytes(value)
    return value


def runtime_contract_digest() -> str:
    return digest(validate_runtime_contract())


def _derive(prefix: str, *parts: object) -> str:
    message = "\0".join((prefix, *(str(part) for part in parts)))
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def derive_session_token(package_id: str, execution_token: str) -> str:
    _require(package_id.startswith("network-validation-execution-"), "invalid package ID")
    _require(HEX24.fullmatch(execution_token) is not None, "invalid execution token")
    return _derive("network-validation-session-v1", package_id, execution_token)[:24]


def derive_attempt_id(package_id: str, execution_token: str, attempt_number: int) -> str:
    _require(attempt_number in (1, 2), "attempt number outside frozen limit")
    return _derive("network-validation-attempt-v1", package_id, execution_token, attempt_number)[:24]


def derive_runtime_namespace(package_digest: str, attempt_id: str) -> str:
    _require(HEX64.fullmatch(package_digest) is not None, "invalid package digest")
    _require(HEX24.fullmatch(attempt_id) is not None, "invalid attempt ID")
    value = f"filin-nv-{package_digest[:12]}-{attempt_id}"
    _require(len(value) <= 63, "runtime namespace too long")
    return value


@dataclass(frozen=True)
class SessionIdentity:
    package_id: str
    package_digest: str
    execution_token: str
    scenario_token: str
    session_token: str
    attempt_id: str
    attempt_number: int
    runtime_namespace: str


def session_identity(package: dict[str, Any], unit: dict[str, Any], attempt_number: int) -> SessionIdentity:
    session_token = derive_session_token(package["package_id"], unit["execution_token"])
    attempt_id = derive_attempt_id(package["package_id"], unit["execution_token"], attempt_number)
    return SessionIdentity(
        package_id=package["package_id"],
        package_digest=package["canonical_digest"],
        execution_token=unit["execution_token"],
        scenario_token=unit["scenario_token"],
        session_token=session_token,
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        runtime_namespace=derive_runtime_namespace(package["canonical_digest"], attempt_id),
    )


@dataclass(frozen=True)
class SessionPaths:
    session_root: Path
    staging: Path
    sealed: Path
    failed: Path


def session_paths(output_root: Path, identity: SessionIdentity) -> SessionPaths:
    root = output_root / "sessions" / identity.session_token
    return SessionPaths(
        session_root=root,
        staging=root / f".attempt-{identity.attempt_number:02d}.staging",
        sealed=root / f"attempt-{identity.attempt_number:02d}",
        failed=root / f"attempt-{identity.attempt_number:02d}.failed",
    )


def validate_unused_paths(paths: SessionPaths) -> None:
    _require(not any(path.exists() for path in (paths.staging, paths.sealed, paths.failed)), "attempt output path already exists")


@contextmanager
def _exclusive_lock(target: Path) -> Iterator[None]:
    lock = target.with_name(f".{target.name}.lock")
    descriptor: int | None = None
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        yield
    except FileExistsError as error:
        raise ContractError(f"concurrent append rejected: {target.name}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if lock.exists():
            lock.unlink()


class LedgerStore:
    def __init__(self, path: Path, package_id: str, package_digest: str) -> None:
        self.path = path
        self.package_id = package_id
        self.package_digest = package_digest
        self.contract = validate_runtime_contract()

    def read(self) -> list[dict[str, Any]]:
        _require(self.path.is_file(), "campaign ledger missing")
        records = validate_ledger_bytes(self.path.read_bytes(), self.package_id, self.package_digest)
        for record in records:
            self._validate_record(record)
        self._validate_transitions(records)
        return records

    def _validate_transitions(self, records: list[dict[str, Any]]) -> None:
        machine = self.contract["ledger_state_machine"]
        transitions = machine["transitions"]
        run_plan = load_json(RUN_PLAN_PATH)
        validate_run_plan(run_plan)
        units = run_plan["ordered_execution_units"]
        by_token = {unit["execution_token"]: unit for unit in units}
        states: dict[str, str] = {}
        completed: set[str] = set()
        open_token: str | None = None
        for record in records:
            token = record["execution_token"]
            _require(token in by_token, "runtime ledger execution token absent from run plan")
            _require(record["scenario_token"] == by_token[token]["scenario_token"], "runtime ledger scenario binding mismatch")
            state = states.get(token, machine["initial"])
            key = f"{state}:{record['event_type']}:{record['attempt_number']}"
            _require(key in transitions, "runtime ledger lifecycle transition mismatch")
            if record["event_type"] == "session_started" and state == machine["initial"]:
                expected = next(unit["execution_token"] for unit in units if unit["execution_token"] not in completed)
                _require(token == expected, "runtime ledger run-plan order mismatch")
            if open_token is not None:
                _require(token == open_token, "runtime ledger contains interleaved execution units")
            state = transitions[key]
            states[token] = state
            if state == "completed":
                completed.add(token)
            if state in machine["terminal_states"]:
                open_token = None
            else:
                open_token = token

    def _validate_record(self, record: dict[str, Any]) -> None:
        profile = self.contract["ledger_record_profile"]
        _require(set(record) == set(profile["exact_fields"]), "runtime ledger record fields mismatch")
        event = record.get("event_type")
        _require(event in profile["event_status"], "runtime ledger event rejected")
        _require(record.get("status") == profile["event_status"][event], "runtime ledger event status mismatch")
        _require(record.get("attempt_number") in (1, 2), "runtime ledger attempt number mismatch")
        _require(HEX24.fullmatch(str(record.get("execution_token", ""))) is not None, "runtime ledger execution token mismatch")
        _require(record.get("session_token") == derive_session_token(self.package_id, record["execution_token"]), "runtime ledger session token mismatch")
        _require(record.get("attempt_id") == derive_attempt_id(self.package_id, record["execution_token"], record["attempt_number"]), "runtime ledger attempt ID mismatch")
        _require(UTC_RFC3339.fullmatch(str(record.get("occurred_at", ""))) is not None, "runtime ledger timestamp mismatch")
        reason = profile["reason_code"][event]
        if reason is None:
            _require(record.get("reason_code") is None, "unexpected ledger reason code")
        elif reason == "required_non_empty":
            _require(isinstance(record.get("reason_code"), str) and bool(record["reason_code"]), "ledger failure reason missing")
        else:
            allowed = set(load_json(EXECUTION / "campaign_ledger_contract_v2.json")["retry_reason_allowlist"])
            _require(record.get("reason_code") in allowed, "ledger retry reason rejected")

    def next_sequence_and_previous(self) -> tuple[int, str]:
        records = self.read()
        return (len(records) + 1, records[-1]["record_digest"] if records else "0" * 64)

    def attempts_for(self, execution_token: str) -> int:
        return sum(record["event_type"] == "session_started" and record["execution_token"] == execution_token for record in self.read())

    def completed_tokens(self) -> set[str]:
        return {record["execution_token"] for record in self.read() if record["event_type"] == "session_completed"}

    def active_tokens(self) -> set[str]:
        active: set[str] = set()
        for record in self.read():
            token = record["execution_token"]
            if record["event_type"] == "session_started":
                active.add(token)
            elif record["event_type"] in {"session_completed", "session_failed"}:
                active.discard(token)
        return active

    def append(self, identity: SessionIdentity, event_type: str, *, reason_code: str | None = None, occurred_at: str | None = None) -> dict[str, Any]:
        with _exclusive_lock(self.path):
            existing = self.read()
            sequence = len(existing) + 1
            previous = existing[-1]["record_digest"] if existing else "0" * 64
            status = self.contract["ledger_record_profile"]["event_status"].get(event_type)
            _require(status is not None, "runtime ledger event rejected")
            record: dict[str, Any] = {
                "record_sequence": sequence,
                "attempt_id": identity.attempt_id,
                "attempt_number": identity.attempt_number,
                "event_type": event_type,
                "previous_record_digest": previous,
                "record_digest": "",
                "package_id": identity.package_id,
                "package_canonical_digest": identity.package_digest,
                "execution_token": identity.execution_token,
                "scenario_token": identity.scenario_token,
                "session_token": identity.session_token,
                "status": status,
                "reason_code": reason_code,
                "occurred_at": occurred_at or utc_now(),
            }
            record["record_digest"] = ledger_record_digest(record)
            self._validate_record(record)
            self._validate_transitions([*existing, record])
            encoded = canonical_bytes(record) + b"\n"
            with self.path.open("ab", buffering=0) as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            validated = self.read()
            _require(validated[-1] == record, "ledger post-append validation failed")
            return record


def resolve_next_unit(ledger: LedgerStore, run_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    run_plan = run_plan or load_json(RUN_PLAN_PATH)
    validate_run_plan(run_plan)
    active = ledger.active_tokens()
    _require(not active, "existing active scientific attempt must be resolved")
    completed = ledger.completed_tokens()
    for unit in run_plan["ordered_execution_units"]:
        if unit["execution_token"] not in completed:
            return unit
    raise ContractError("phase1 run plan is already complete")


def _restrict_windows_acl(path: Path) -> None:
    if os.name != "nt":
        os.chmod(path, 0o600)
        return
    whoami = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"], check=True, capture_output=True, text=True).stdout
    operator_sid = next(__import__("csv").reader([whoami.strip()]))[1]
    subprocess.run([
        "icacls.exe", str(path), "/inheritance:r", "/grant:r",
        f"*{operator_sid}:F", "*S-1-5-18:F", "*S-1-5-32-544:F",
    ], check=True, capture_output=True)


class MappingStore:
    def __init__(self, secret_root: Path, package_id: str, package_digest: str, secret: bytes) -> None:
        self.path = secret_root / validate_runtime_contract()["mapping_lifecycle"]["relative_path"]
        self.package_id = package_id
        self.package_digest = package_digest
        self.secret = secret
        mapping_secret_fingerprint(secret)

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        content = self.path.read_bytes()
        _require(not content.startswith(b"\xef\xbb\xbf") and b"\r" not in content, "mapping physical format mismatch")
        _require(not content or content.endswith(b"\n"), "mapping final line truncated")
        rows = [json.loads(line.decode("utf-8")) for line in content.splitlines()]
        seen: set[str] = set()
        exact = set(validate_runtime_contract()["mapping_lifecycle"]["entry_exact_fields"])
        for row, raw in zip(rows, content.splitlines()):
            _require(set(row) == exact, "mapping entry fields mismatch")
            _require(row.get("schema_version") == MAPPING_ENTRY_SCHEMA, "mapping entry schema mismatch")
            _require(row.get("package_id") == self.package_id and row.get("package_canonical_digest") == self.package_digest, "mapping package binding mismatch")
            _require(HEX24.fullmatch(str(row.get("execution_token", ""))) is not None, "mapping execution token mismatch")
            _require(row.get("evaluation_token") == evaluation_token(self.secret, row["execution_token"]), "mapping token mismatch")
            _require(UTC_RFC3339.fullmatch(str(row.get("created_at", ""))) is not None, "mapping timestamp mismatch")
            _require(raw == canonical_bytes(row), "mapping entry is not canonical JSON")
            _require(row["execution_token"] not in seen, "duplicate mapping execution token")
            seen.add(row["execution_token"])
        return rows

    def ensure(self, execution_token: str, *, created_at: str | None = None) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.path):
            rows = self.read()
            expected_token = evaluation_token(self.secret, execution_token)
            existing = [row for row in rows if row["execution_token"] == execution_token]
            if existing:
                _require(existing[0]["evaluation_token"] == expected_token, "SESSION_MAPPING_CONFLICT")
                return existing[0]
            row = {
                "schema_version": MAPPING_ENTRY_SCHEMA,
                "package_id": self.package_id,
                "package_canonical_digest": self.package_digest,
                "execution_token": execution_token,
                "evaluation_token": expected_token,
                "created_at": created_at or utc_now(),
            }
            encoded = canonical_bytes(row) + b"\n"
            created = not self.path.exists()
            if created:
                temporary = self.path.with_name(f".{self.path.name}.{secrets.token_hex(12)}.tmp")
                try:
                    with temporary.open("xb", buffering=0) as stream:
                        stream.write(encoded)
                        stream.flush()
                        os.fsync(stream.fileno())
                    _restrict_windows_acl(temporary)
                    temporary.replace(self.path)
                finally:
                    if temporary.exists():
                        temporary.unlink()
            else:
                _restrict_windows_acl(self.path)
                with self.path.open("ab", buffering=0) as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            _require(self.read()[-1] == row, "mapping post-append validation failed")
            return row


def validate_feature_row(value: dict[str, Any], expected_evaluation_token: str, feature_names: list[str], package: dict[str, Any]) -> dict[str, Any]:
    exact = set(validate_runtime_contract()["artifact_schemas"]["feature_rows.jsonl"]["exact_fields"])
    _require(set(value) == exact, "feature row fields mismatch")
    _require(value.get("schema_version") == FEATURE_ROW_SCHEMA, "feature row schema mismatch")
    _require(value.get("evaluation_token") == expected_evaluation_token, "feature row evaluation token mismatch")
    _require(value.get("feature_contract_digest") == package["feature_contract_digest"], "feature contract digest mismatch")
    _require(value.get("feature_order_digest") == package["feature_order_digest"], "feature order digest mismatch")
    row = value.get("feature_row")
    _require(isinstance(row, list) and len(row) == 51 and len(feature_names) == 51, "feature row cardinality mismatch")
    _require(all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(float(item)) for item in row), "feature row contains non-finite values")
    canonical_bytes(value)
    return value


def build_session_integrity_manifest(
    attempt_root: Path,
    package: dict[str, Any],
    identity: SessionIdentity,
    locked_image_digests: dict[str, str],
) -> dict[str, Any]:
    contract = validate_runtime_contract()
    paths = contract["session_integrity_manifest"]["output_digest_paths"]
    output_digests = {relative: sha256_file(attempt_root / relative) for relative in paths}
    value: dict[str, Any] = {
        "schema_version": SESSION_MANIFEST_SCHEMA,
        "execution_package_digest": package["canonical_digest"],
        "official_freeze_digest": package["superseding_freeze_digest"],
        "scenario_token": identity.scenario_token,
        "session_token": identity.session_token,
        "attempt_id": identity.attempt_id,
        "attempt_number": identity.attempt_number,
        "locked_image_digests": dict(sorted(locked_image_digests.items())),
        "output_digests": output_digests,
        "completion_status": "sealed_success",
        "execution_event_sha256": output_digests["execution_event.json"],
        "marker_events_sha256": output_digests["marker_events.jsonl"],
        "pcap_sha256": output_digests["capture/traffic.pcap"],
        "capture_manifest_sha256": output_digests["capture/capture_manifest.json"],
        "conn_log_sha256": output_digests["zeek/conn.log"],
        "http_log_sha256": output_digests["zeek/http.log"],
        "dns_log_sha256": output_digests["zeek/dns.log"],
        "parameter_realization_sha256": output_digests["parameter_realization.json"],
        "feature_rows_sha256": output_digests["feature_rows.jsonl"],
        "session_manifest_canonical_sha256": "",
    }
    value["session_manifest_canonical_sha256"] = digest({key: item for key, item in value.items() if key != "session_manifest_canonical_sha256"})
    validate_session_integrity_manifest(value, attempt_root, package, identity, locked_image_digests)
    return value


def validate_session_integrity_manifest(
    value: dict[str, Any],
    attempt_root: Path,
    package: dict[str, Any],
    identity: SessionIdentity,
    locked_image_digests: dict[str, str],
) -> dict[str, Any]:
    contract = validate_runtime_contract()
    _require(set(value) == set(contract["session_integrity_manifest"]["exact_fields"]), "session manifest fields mismatch")
    _require(value.get("schema_version") == SESSION_MANIFEST_SCHEMA, "session manifest schema mismatch")
    bindings = {
        "execution_package_digest": package["canonical_digest"],
        "official_freeze_digest": package["superseding_freeze_digest"],
        "scenario_token": identity.scenario_token,
        "session_token": identity.session_token,
        "attempt_id": identity.attempt_id,
        "attempt_number": identity.attempt_number,
        "locked_image_digests": dict(sorted(locked_image_digests.items())),
        "completion_status": "sealed_success",
    }
    _require(all(value.get(key) == expected for key, expected in bindings.items()), "session manifest binding mismatch")
    paths = contract["session_integrity_manifest"]["output_digest_paths"]
    expected_digests = {relative: sha256_file(attempt_root / relative) for relative in paths}
    _require(value.get("output_digests") == expected_digests, "session output digest mismatch")
    individual = {
        "execution_event_sha256": "execution_event.json",
        "marker_events_sha256": "marker_events.jsonl",
        "pcap_sha256": "capture/traffic.pcap",
        "capture_manifest_sha256": "capture/capture_manifest.json",
        "conn_log_sha256": "zeek/conn.log",
        "http_log_sha256": "zeek/http.log",
        "dns_log_sha256": "zeek/dns.log",
        "parameter_realization_sha256": "parameter_realization.json",
        "feature_rows_sha256": "feature_rows.jsonl",
    }
    _require(all(value.get(field) == expected_digests[path] for field, path in individual.items()), "session digest field mismatch")
    expected_self = digest({key: item for key, item in value.items() if key != "session_manifest_canonical_sha256"})
    _require(value.get("session_manifest_canonical_sha256") == expected_self, "session manifest self digest mismatch")
    canonical_bytes(value)
    return value


def validate_campaign_initialization(
    package: dict[str, Any],
    output_root: Path,
    secret_root: Path,
    expected_fingerprint: str | None = None,
) -> tuple[LedgerStore, MappingStore]:
    secret_path = secret_root / "mapping-secret.bin"
    metadata_path = secret_root / "mapping-secret.metadata.json"
    manifest_path = output_root / "control" / "campaign-initialization.json"
    ledger_path = output_root / "control" / "campaign-ledger.jsonl"
    _require(all(path.is_file() for path in (secret_path, metadata_path, manifest_path, ledger_path)), "campaign initialization files missing")
    secret = secret_path.read_bytes()
    fingerprint = mapping_secret_fingerprint(secret)
    if expected_fingerprint is not None:
        _require(fingerprint == expected_fingerprint, "mapping secret fingerprint mismatch")
    metadata = load_json(metadata_path)
    _require(metadata.get("package_id") == package["package_id"] and metadata.get("package_canonical_digest") == package["canonical_digest"], "secret metadata package binding mismatch")
    _require(metadata.get("secret_fingerprint") == fingerprint, "secret metadata fingerprint mismatch")
    manifest = load_json(manifest_path)
    validate_initialization_manifest(manifest, package, fingerprint)
    ledger = LedgerStore(ledger_path, package["package_id"], package["canonical_digest"])
    ledger.read()
    mapping = MappingStore(secret_root, package["package_id"], package["canonical_digest"], secret)
    mapping.read()
    return ledger, mapping
