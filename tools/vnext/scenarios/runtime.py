"""Локальное исполнение wave 1 без доступа к внешним целям и научных запусков."""
from __future__ import annotations

import hashlib
import http.client
import inspect
import json
import random
import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol
from urllib.parse import parse_qs

from tools.vnext.contracts import ContractError, canonical_bytes, canonical_digest
from tools.vnext.telemetry import (
    assert_no_ground_truth_leakage,
    build_scenario_realization,
    validate_normalized_event,
    validate_observation_bundle,
    validate_scenario_realization,
    with_digest,
)


@dataclass(frozen=True)
class SafetyLimits:
    max_requests: int = 48
    max_duration_seconds: float = 8.0
    max_concurrency: int = 4

    def validate(self) -> None:
        if not 1 <= self.max_requests <= 64:
            raise ContractError("request limit outside the disposable profile")
        if not 0 < self.max_duration_seconds <= 10:
            raise ContractError("duration limit outside the disposable profile")
        if not 1 <= self.max_concurrency <= 4:
            raise ContractError("concurrency limit outside the disposable profile")


@dataclass(frozen=True)
class TargetCapabilities:
    target_id: str
    host: str
    http_port: int
    tcp_ports: tuple[int, ...]
    capabilities: frozenset[str]
    disposable: bool = True
    network_scope: str = "loopback"

    @property
    def allowlisted_endpoints(self) -> frozenset[tuple[str, int]]:
        return frozenset((self.host, port) for port in self.tcp_ports)


@dataclass(frozen=True)
class ExecutionContext:
    environment_id: str
    limits: SafetyLimits
    deadline_monotonic: float


@dataclass(frozen=True)
class ExecutionResult:
    started_at: str
    finished_at: str
    exit_status: str
    observable_execution_metadata: dict[str, Any]
    raw_records: tuple[dict[str, Any], ...]
    runtime_diagnostics: tuple[str, ...] = ()


class ScenarioGenerator(Protocol):
    generator_id: str
    family: str

    def execute(self, definition: dict[str, Any], realization: dict[str, Any], context: ExecutionContext, target: TargetCapabilities) -> ExecutionResult: ...


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _guard(definition: dict[str, Any], realization: dict[str, Any], context: ExecutionContext, target: TargetCapabilities) -> None:
    context.limits.validate()
    loopback = target.network_scope == "loopback" and target.host in {"127.0.0.1", "::1", "localhost"}
    docker_lab = target.network_scope == "docker_internal" and context.environment_id == "vnext-docker-lab" and target.host in {"target-http", "target-auth"}
    if not target.disposable or not (loopback or docker_lab):
        raise ContractError("wave 1 execution is restricted to an allowlisted disposable target")
    required = set(definition["environment_requirements"]["target_capabilities"])
    if not required <= target.capabilities:
        raise ContractError(f"target capability mismatch: {sorted(required - target.capabilities)}")
    if realization["environment_binding"]["target_id"] != target.target_id:
        raise ContractError("realization target is not the allowlisted target")
    request_count = int(realization["resolved_parameters"].get("request_count", 1))
    if request_count > context.limits.max_requests:
        raise ContractError("realization exceeds the request limit")


def _connect(target: TargetCapabilities, port: int) -> dict[str, Any]:
    if (target.host, port) not in target.allowlisted_endpoints:
        raise ContractError("connection endpoint is not allowlisted")
    started = _utc()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.15)
    try:
        code = sock.connect_ex((target.host, port))
        source_ip = sock.getsockname()[0]
    finally:
        sock.close()
    return {"kind": "connection", "timestamp": started, "source_ip": source_ip, "destination_ip": socket.gethostbyname(target.host), "destination_port": port, "transport": "tcp", "state": "established" if code == 0 else "refused"}


def _http(target: TargetCapabilities, method: str, path: str, body: str = "") -> dict[str, Any]:
    if (target.host, target.http_port) not in target.allowlisted_endpoints:
        raise ContractError("HTTP endpoint is not allowlisted")
    connection = http.client.HTTPConnection(target.host, target.http_port, timeout=0.5)
    headers = {"Content-Type": "application/x-www-form-urlencoded"} if body else {}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    source_ip = connection.sock.getsockname()[0] if connection.sock else "127.0.0.1"
    connection.close()
    return {"kind": "http", "timestamp": _utc(), "source_ip": source_ip, "destination_ip": socket.gethostbyname(target.host), "destination_port": target.http_port, "method": method, "path": path, "status_code": response.status, "request_bytes": len(body.encode()), "response_bytes": len(payload)}


def _result(started: str, records: list[dict[str, Any]], operation: str, network_scope: str) -> ExecutionResult:
    expanded: list[dict[str, Any]] = []
    for row in records:
        if row["kind"] == "http":
            expanded.append({"kind": "connection", "timestamp": row["timestamp"], "source_ip": row["source_ip"], "destination_ip": row["destination_ip"], "destination_port": row["destination_port"], "transport": "tcp", "state": "established"})
        expanded.append(row)
    return ExecutionResult(started, _utc(), "completed", {"operation": operation, "record_count": len(expanded), "transport": network_scope}, tuple(expanded))


def _pause(milliseconds: float, context: ExecutionContext) -> None:
    if time.monotonic() >= context.deadline_monotonic:
        raise ContractError("execution deadline reached")
    time.sleep(min(max(milliseconds, 0.0), 10.0) / 1000.0)


class ReconFamilyA:
    generator_id, family = "wave1_recon_family_a", "recon_a_sequential_socket"

    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc()
        count = min(int(realization["resolved_parameters"]["request_count"]), len(target.tcp_ports))
        ports = list(target.tcp_ports)[:count]
        records = []
        for index, port in enumerate(ports):
            if index: _pause(float(realization["resolved_parameters"].get("spacing_ms", 0)), context)
            records.append(_connect(target, port))
        return _result(started, records, "tcp-capability-check", target.network_scope)


class ReconFamilyB:
    generator_id, family = "wave1_recon_family_b", "recon_b_interleaved_probe"

    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc()
        count = min(int(realization["resolved_parameters"]["request_count"]), len(target.tcp_ports))
        rng = random.Random(realization["seed"] ^ 0xB17E)
        ports = list(target.tcp_ports); rng.shuffle(ports)
        records: list[dict[str, Any]] = []
        left, right = ports[:count:2], list(reversed(ports[1:count:2]))
        for index in range(max(len(left), len(right))):
            if records: _pause(float(realization["resolved_parameters"].get("spacing_ms", 0)), context)
            if index < len(left): records.append(_connect(target, left[index]))
            if index < len(right): records.append(_connect(target, right[index]))
        return _result(started, records, "interleaved-tcp-inventory", target.network_scope)


class WebEnumerationGenerator:
    generator_id, family = "wave1_web_enumerator", "web_dictionary_walk"
    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc()
        paths = ["/", "/status", "/docs", "/admin", "/api/items", "/missing"]
        records = []
        for index, path in enumerate(paths[:int(realization["resolved_parameters"]["request_count"])]):
            if index: _pause(float(realization["resolved_parameters"].get("spacing_ms", 0)), context)
            records.append(_http(target, "GET", path))
        return _result(started, records, "http-resource-discovery", target.network_scope)


class CredentialFamilyA:
    generator_id, family = "wave1_credential_family_a", "credential_a_account_concentrated"
    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc(); p = realization["resolved_parameters"]
        accounts = ["alex", "maria", "sam", "dana"][:int(p.get("account_count", 2))]
        records = []; attempts_done = 0; attempt_budget = int(p["request_count"])
        for account in accounts:
            for attempt in range(int(p.get("attempts_per_account", 2))):
                if attempts_done >= attempt_budget: break
                if records: _pause(float(p.get("spacing_ms", 0)), context)
                http_row = _http(target, "POST", "/login", f"account={account}&secret=trial{attempt}")
                records.extend((http_row, {"kind": "auth", "timestamp": http_row["timestamp"], "account": account, "success": http_row["status_code"] < 400}))
                attempts_done += 1
        return _result(started, records, "credential-validation", target.network_scope)


class CredentialFamilyB:
    generator_id, family = "wave1_credential_family_b", "credential_b_round_robin"
    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc(); p = realization["resolved_parameters"]
        accounts = ["maria", "dana", "alex", "sam"][:int(p.get("account_count", 3))]
        pairs = [(account, attempt) for attempt in range(int(p.get("attempts_per_account", 1))) for account in accounts][:int(p["request_count"])]
        records = []
        for account, attempt in pairs:
            if records: _pause(float(p.get("spacing_ms", 0)), context)
            http_row = _http(target, "POST", "/session", f"user={account}&password=guess{attempt}")
            records.extend((http_row, {"kind": "auth", "timestamp": http_row["timestamp"], "account": account, "success": http_row["status_code"] < 400}))
        return _result(started, records, "round-robin-authentication", target.network_scope)


class BeaconFamilyA:
    generator_id, family = "wave1_beacon_family_a", "beacon_a_new_connection"
    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc(); p = realization["resolved_parameters"]
        records = []
        rng = random.Random(realization["seed"] ^ 0xA11CE)
        for index in range(int(p["request_count"])):
            if index:
                base = float(p.get("interval_ms", 0)); jitter = float(p.get("jitter_ratio", 0))
                _pause(base * (1 + rng.uniform(-jitter, jitter)), context)
            records.append(_http(target, "GET", "/api/pulse"))
        return _result(started, records, "periodic-http-client", target.network_scope)


class BeaconFamilyB:
    generator_id, family = "wave1_beacon_family_b", "beacon_b_persistent_session"
    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc(); p = realization["resolved_parameters"]
        connection = http.client.HTTPConnection(target.host, target.http_port, timeout=0.5); records = []
        for index in range(int(p["request_count"])):
            if index: _pause(float(p.get("interval_ms", 0)) * (0.5 if index % 2 else 1.5), context)
            path = "/status" if index % 2 == 0 else "/api/pulse"
            connection.request("GET", path); response = connection.getresponse(); data = response.read()
            source_ip = connection.sock.getsockname()[0] if connection.sock else "127.0.0.1"
            records.append({"kind": "http", "timestamp": _utc(), "source_ip": source_ip, "destination_ip": socket.gethostbyname(target.host), "destination_port": target.http_port, "method": "GET", "path": path, "status_code": response.status, "request_bytes": 0, "response_bytes": len(data)})
        connection.close(); return _result(started, records, "persistent-http-session", target.network_scope)


class BenignOperationsGenerator:
    generator_id, family = "wave1_benign_operations", "approved_operations"
    def execute(self, definition, realization, context, target):
        _guard(definition, realization, context, target); started = _utc(); variant = definition["scenario_variant"]; records = []
        count = int(realization["resolved_parameters"]["request_count"])
        if variant in {"service_monitoring", "approved_scanner"}:
            ports = list(target.tcp_ports)[::2] if variant == "service_monitoring" else list(target.tcp_ports)
            records = [_connect(target, port) for port in ports[:count]]
        elif variant in {"auth_misconfiguration", "password_mistakes"}:
            account = "maria" if variant == "auth_misconfiguration" else "alex"
            attempts = 1 if variant == "password_mistakes" else min(count, 3)
            for _ in range(attempts):
                http_row = _http(target, "POST", "/login", f"account={account}&secret=incorrect")
                records.extend((http_row, {"kind": "auth", "timestamp": http_row["timestamp"], "account": account, "success": http_row["status_code"] < 400}))
        else:
            paths = ["/status", "/api/items", "/docs"]
            if variant == "normal_navigation": paths = ["/", "/docs", "/api/items", "/status"]
            for index in range(count):
                if index: _pause(float(realization["resolved_parameters"].get("interval_ms", realization["resolved_parameters"].get("spacing_ms", 0))), context)
                records.append(_http(target, "GET", paths[index % len(paths)]))
        return _result(started, records, "approved-local-operation", target.network_scope)


GENERATORS: dict[str, ScenarioGenerator] = {item.generator_id: item for item in (
    ReconFamilyA(), ReconFamilyB(), WebEnumerationGenerator(), CredentialFamilyA(), CredentialFamilyB(), BeaconFamilyA(), BeaconFamilyB(), BenignOperationsGenerator()
)}


def assert_generator_family_independence(generator_ids: list[str]) -> None:
    rows = [GENERATORS[item] for item in generator_ids]
    if len(rows) < 2:
        raise ContractError("two generator families are required")
    classes = {type(row) for row in rows}; families = {row.family for row in rows}
    entrypoints = {f"{type(row).__module__}.{type(row).__qualname__}.execute" for row in rows}
    source_hashes = {hashlib.sha256(inspect.getsource(type(row).execute).encode()).hexdigest() for row in rows}
    if min(len(classes), len(families), len(entrypoints), len(source_hashes)) != len(rows):
        raise ContractError("generator families are aliases or share an implementation")


def build_realization(definition: dict[str, Any], generator_id: str, seed: int, target: TargetCapabilities) -> dict[str, Any]:
    if generator_id not in definition["generator_requirements"]["allowed_generator_ids"] or generator_id not in GENERATORS:
        raise ContractError("generator is not compatible with the scenario")
    defaults = dict(definition["intensity_model"]["default_profile"])
    rng = random.Random(seed)
    if "scan_ordering" in defaults and defaults["scan_ordering"] == "seeded":
        defaults["scan_ordering"] = rng.choice(["ascending", "interleaved"])
    realization = build_scenario_realization(
        definition, generator_id, seed, defaults,
        {"environment_id": "vnext-docker-lab" if target.network_scope == "docker_internal" else "wave1-disposable", "services": sorted(target.capabilities), "target_id": target.target_id},
        {"vault_id": "sealed-wave1", "label_id": "external-only"},
    )
    return validate_scenario_realization(realization)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *_args): pass
    def _reply(self, status: int, body: bytes):
        self.send_response(status); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        known = {"/", "/status", "/docs", "/api/items", "/api/pulse", "/admin"}
        self._reply(200 if self.path in known else 404, b"ok" if self.path in known else b"not found")
    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0")); values = parse_qs(self.rfile.read(size).decode("utf-8", "replace"))
        account = (values.get("account") or values.get("user") or [""])[0]
        secret = (values.get("secret") or values.get("password") or [""])[0]
        self._reply(200 if account == "alex" and secret == "correct-horse" else 401, b"accepted" if account == "alex" and secret == "correct-horse" else b"denied")


class DisposableTarget:
    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        port = self.server.server_address[1]
        candidates = tuple(dict.fromkeys((port, max(1025, port - 1), min(65535, port + 1), max(1025, port - 2), min(65535, port + 2), max(1025, port - 3))))
        self.target = TargetCapabilities("wave1-loopback", "127.0.0.1", port, candidates, frozenset({"http_service", "authentication_service", "generic_tcp_services", "http_callback"}))
        return self.target
    def __exit__(self, *_args):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)


def _raw_artifact(records: tuple[dict[str, Any], ...], path: Path) -> dict[str, Any]:
    data = b"".join(canonical_bytes(row) + b"\n" for row in records); path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    return {"evidence_id": "raw_" + digest, "artifact_type": "jsonl", "sha256": digest, "size_bytes": len(data), "locator": "raw/activity.jsonl"}


def _entity_id(kind: str, value: str) -> str:
    return "ent_" + canonical_digest({"kind": kind, "value": value})


def _normalize(records: tuple[dict[str, Any], ...], raw: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for sequence, row in enumerate(records):
        parsed_digest = canonical_digest(row)
        event_type = {"connection": "network.flow", "http": "http.request", "auth": "auth.attempt"}[row["kind"]]
        if event_type == "network.flow":
            payload = {"namespace": event_type, "source": {"ip": row["source_ip"]}, "destination": {"ip": row["destination_ip"], "port": row["destination_port"]}, "transport": row["transport"], "bytes": 0, "packets": 1, "connection_state": row["state"]}
        elif event_type == "auth.attempt":
            payload = {"namespace": event_type, "account_entity_id": _entity_id("account", row["account"]), "authentication_type": "password", "success": row["success"], "failure_reason": "invalid_credentials" if not row["success"] else "none"}
        else:
            payload = {"namespace": event_type, "method": row["method"], "scheme": "http", "host": row["destination_ip"], "path": row["path"], "status_code": row["status_code"], "request_bytes": row["request_bytes"], "response_bytes": row["response_bytes"]}
        entity_refs = []
        source_ip = row.get("source_ip", "127.0.0.1"); destination_ip = row.get("destination_ip", "127.0.0.1")
        entity_refs.append({"role": "source", "entity_id": _entity_id("ip", source_ip), "entity_type": "ip"})
        entity_refs.append({"role": "destination", "entity_id": _entity_id("ip", destination_ip), "entity_type": "ip"})
        if event_type == "auth.attempt":
            entity_refs.append({"role": "target", "entity_id": _entity_id("service", "local-authentication"), "entity_type": "service"})
            payload["target_service_entity_id"] = _entity_id("service", "local-authentication")
        base = {"schema_version": "normalized_security_event_v1", "event_type": event_type, "stage": "normalized",
                "source": {"source_type": "local_service_telemetry", "source_product": "disposable_http_tcp_target", "source_component": "activity_log", "collector": "wave1_local_normalizer", "collector_version": "v1"},
                "temporal": {"event_timestamp": row["timestamp"], "ingest_timestamp": _utc(), "ordering": {"domain": "wave1-loopback", "sequence": sequence}}, "entity_refs": entity_refs,
                "action": {"name": "connect" if event_type == "network.flow" else ("authenticate" if event_type == "auth.attempt" else "request"), "outcome": "success" if row.get("state") == "established" or row.get("status_code", 500) < 400 or row.get("success") is True else "failure", "status": row.get("state", str(row.get("status_code", "accepted" if row.get("success") else "denied")))},
                "payload": payload, "provenance": {"source_record_id": f"activity:{sequence}", "raw_evidence": {**raw, "record_offset": sequence}, "transformation_chain": [
                    {"stage": "parsed", "component": "jsonl_parser", "version": "v1", "input_digest": raw["sha256"], "output_digest": parsed_digest},
                    {"stage": "normalized", "component": "wave1_local_normalizer", "version": "v1", "input_digest": parsed_digest, "output_digest": canonical_digest(payload)}]}, "enrichments": []}
        event = with_digest(base, id_field="event_id", id_prefix="evt"); validate_normalized_event(event); events.append(event)
    return events


def _bundle(events: list[dict[str, Any]], raw: dict[str, Any]) -> dict[str, Any]:
    times = [event["temporal"]["event_timestamp"] for event in events]
    base = {"schema_version": "observation_bundle_v1", "window": {"start": min(times), "end": max(times), "ordering_domain": "wave1-loopback"},
            "event_refs": [{"event_id": row["event_id"], "canonical_digest": row["canonical_digest"]} for row in events], "entity_refs": [],
            "aggregation": {"method": "execution_window", "builder": "wave1_observation_builder", "builder_version": "v1", "causal": True, "event_count": len(events)},
            "telemetry_capability_refs": sorted({row["event_type"] for row in events}), "raw_evidence_refs": [{"evidence_id": raw["evidence_id"], "sha256": raw["sha256"]}],
            "feature_generation_refs": [], "correlation_context": {"correlation_keys": ["source.ip", "destination.ip"], "parent_bundle_refs": []}, "ground_truth_included": False}
    bundle = with_digest(base, id_field="bundle_id", id_prefix="obs"); validate_observation_bundle(bundle, events=events); return bundle


def run_smoke(definition: dict[str, Any], generator_id: str | None = None, seed: int = 7) -> dict[str, Any]:
    if definition["status"] != "implemented": raise ContractError("planned scenarios cannot be executed")
    generator_id = generator_id or definition["generator_requirements"]["allowed_generator_ids"][0]
    with DisposableTarget() as target, TemporaryDirectory(prefix="filin-wave1-") as directory:
        realization = build_realization(definition, generator_id, seed, target)
        context = ExecutionContext("wave1-disposable", SafetyLimits(), time.monotonic() + 8)
        result = GENERATORS[generator_id].execute(definition, realization, context, target)
        if time.monotonic() > context.deadline_monotonic: raise ContractError("execution exceeded its deadline")
        raw = _raw_artifact(result.raw_records, Path(directory) / "activity.jsonl")
        events = _normalize(result.raw_records, raw); bundle = _bundle(events, raw)
        sealed_ground_truth = {"scenario_id": definition["scenario_id"], "taxonomy_node_id": definition["taxonomy_node_id"], "realization_id": realization["realization_id"]}
        assert_no_ground_truth_leakage([result.observable_execution_metadata, list(result.raw_records), events, bundle])
        return {"result": result, "realization": realization, "raw_evidence": raw, "events": events, "observation_bundle": bundle, "sealed_ground_truth": sealed_ground_truth, "temporary_outputs_removed_on_return": True}
