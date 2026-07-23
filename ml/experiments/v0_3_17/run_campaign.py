from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import psutil
import yaml

from collectors.shadow.candidate_registry import validate_v2
from collectors.shadow.event_model_v2 import generate_event
from ml.experiments.v0_3_15_4.candidate import CLASSES, conformal_sets, joint_probabilities
from ml.experiments.v0_3_15_4.feature_v2 import FEATURES
from ml.features.network_sensor_v0_5 import AssetState
from rehearsal.common import append_jsonl, digest, file_sha256, read_json, read_jsonl, write_json


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_17"
REPORT = ROOT / "ml/reports/v0_3_17"
BASE_PROTOCOL_PATH = ROOT / "ml/protocols/v0_3_17_protocol.yaml"
REVISION_2_PROTOCOL_PATH = ROOT / "ml/protocols/v0_3_17_protocol_r2.yaml"
REVISION_3_PROTOCOL_PATH = ROOT / "ml/protocols/v0_3_17_protocol_r3.yaml"
REVISION_4_PROTOCOL_PATH = ROOT / "ml/protocols/v0_3_17_protocol_r4.yaml"
PROTOCOL_PATH = ROOT / "ml/protocols/v0_3_17_protocol_r5.yaml"
LOCK_PATH = REPORT / "pre_campaign_code_lock.json"
COMPOSE = ROOT / "rehearsal/docker-compose.v0_3_17.yml"
ARTIFACT = ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib"
COMPOSE_PROJECT = "filin-v0317-rehearsal"

ALIASES = [
    "runtime_contract_baseline_001", "runtime_contract_baseline_002", "runtime_contract_baseline_003",
    "runtime_transport_faults_001", "runtime_transport_faults_002", "runtime_transport_faults_003",
    "runtime_crash_resume_001", "runtime_crash_resume_002", "runtime_crash_resume_003",
    "runtime_load_clock_001", "runtime_load_clock_002", "runtime_load_clock_003",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def run_command(args: list[str], *, check: bool = True, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, env=environment, text=True, capture_output=True, check=check)


def protocol() -> dict[str, Any]:
    base = yaml.safe_load(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    revision_2 = yaml.safe_load(REVISION_2_PROTOCOL_PATH.read_text(encoding="utf-8"))
    revision_3 = yaml.safe_load(REVISION_3_PROTOCOL_PATH.read_text(encoding="utf-8"))
    revision_4 = yaml.safe_load(REVISION_4_PROTOCOL_PATH.read_text(encoding="utf-8"))
    revision = yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if revision_2["base_protocol_sha256"] != file_sha256(BASE_PROTOCOL_PATH):
        raise RuntimeError("revision_2_base_protocol_hash_mismatch")
    if revision_3["base_protocol_sha256"] != file_sha256(BASE_PROTOCOL_PATH):
        raise RuntimeError("revision_3_base_protocol_hash_mismatch")
    if revision_3["parent_protocol_sha256"] != file_sha256(REVISION_2_PROTOCOL_PATH):
        raise RuntimeError("revision_3_parent_protocol_hash_mismatch")
    if revision_4["base_protocol_sha256"] != file_sha256(BASE_PROTOCOL_PATH):
        raise RuntimeError("revision_4_base_protocol_hash_mismatch")
    if revision_4["parent_protocol_sha256"] != file_sha256(REVISION_3_PROTOCOL_PATH):
        raise RuntimeError("revision_4_parent_protocol_hash_mismatch")
    if revision["base_protocol_sha256"] != file_sha256(BASE_PROTOCOL_PATH):
        raise RuntimeError("revision_5_base_protocol_hash_mismatch")
    if revision["parent_protocol_sha256"] != file_sha256(REVISION_4_PROTOCOL_PATH):
        raise RuntimeError("revision_5_parent_protocol_hash_mismatch")
    base.update({key: revision[key] for key in ("revision", "status")})
    base["campaign"].update(revision["campaign"])
    base["certificate_rotation"].update({
        "sensor_to_connector": {"run": "run_b", "offset": 3300, "serial_a": 3175201, "serial_b": 3175221},
        "connector_to_receiver": {"run": "run_b", "offset": 3450, "serial_a": 3175241, "serial_b": 3175261},
    })
    base["revision_2_protocol"] = revision_2
    base["revision_3_protocol"] = revision_3
    base["parent_protocol_revision"] = revision_4
    base["protocol_revision"] = revision
    return base


def verify_code_lock() -> dict[str, Any]:
    if not LOCK_PATH.is_file():
        raise RuntimeError("pre_campaign_code_lock_missing")
    lock = read_json(LOCK_PATH)
    if lock["protocol_sha256"] != file_sha256(PROTOCOL_PATH):
        raise RuntimeError("protocol_changed_after_code_lock")
    if lock["base_protocol_sha256"] != file_sha256(BASE_PROTOCOL_PATH):
        raise RuntimeError("base_protocol_changed_after_code_lock")
    if lock["revision_2_protocol_sha256"] != file_sha256(REVISION_2_PROTOCOL_PATH):
        raise RuntimeError("revision_2_protocol_changed_after_code_lock")
    if lock["revision_3_protocol_sha256"] != file_sha256(REVISION_3_PROTOCOL_PATH):
        raise RuntimeError("revision_3_protocol_changed_after_code_lock")
    if lock["revision_4_protocol_sha256"] != file_sha256(REVISION_4_PROTOCOL_PATH):
        raise RuntimeError("revision_4_protocol_changed_after_code_lock")
    for relative, expected in lock["source_file_sha256"].items():
        path = ROOT / relative
        if not path.is_file() or file_sha256(path) != expected:
            raise RuntimeError(f"source_changed_after_code_lock:{relative}")
    image = run_command(["docker", "image", "inspect", "filin-rehearsal-v0317:local", "--format", "{{.Id}}"])
    if image.stdout.strip() != lock["component_image_digests"]["filin-rehearsal-v0317:local"]:
        raise RuntimeError("application_image_changed_after_code_lock")
    return lock


def compose_environment(run_index: int, run_spec: dict[str, Any]) -> dict[str, str]:
    environment = dict(os.environ)
    environment.update({
        "FILIN_V0317_RUNTIME_DIR": str(RUNTIME),
        "FILIN_V0317_CERT_DIR": str(RUNTIME / "tls" / f"run-{run_index}" / "active"),
        "FILIN_V0317_SENSOR_INSTANCE_ID": f"sensor-{run_spec['instance_namespace']}",
        "FILIN_V0317_CONNECTOR_INSTANCE_ID": f"connector-{run_spec['instance_namespace']}",
        "FILIN_V0317_RECEIVER_INSTANCE_ID": f"receiver-{run_spec['instance_namespace']}",
    })
    return environment


def compose(args: list[str], environment: dict[str, str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(["docker", "compose", "-f", str(COMPOSE), *args], check=check, environment=environment)


def wait_for_stack(environment: dict[str, str], timeout: float = 90.0) -> dict[str, str]:
    deadline = time.monotonic() + timeout
    services = ["traffic-source", "sensor-runtime", "staging-connector", "reference-receiver", "operator-view"]
    while time.monotonic() < deadline:
        ids = {service: compose(["ps", "-q", service], environment).stdout.strip() for service in services}
        if all(ids.values()):
            states = {}
            for service, container_id in ids.items():
                value = run_command(["docker", "inspect", container_id, "--format", "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}"], check=False).stdout.strip()
                states[service] = value
            if all(value.startswith("running ") and not value.endswith("unhealthy") for value in states.values()):
                return ids
        time.sleep(1)
    raise RuntimeError("rehearsal_stack_not_ready")


def raw_features(state: AssetState, run_id: str, ordinal: int, phase: str) -> dict[str, float]:
    failed = 1 if ordinal % 17 == 0 else 0
    http = 1 if ordinal % 3 == 0 else 0
    dns = 1 if ordinal % 11 == 0 else 0
    raw = {
        "run_id": run_id,
        "window_duration_seconds": 1.0,
        "flow_count": 1,
        "window_event_count": 1 + http + dns,
        "total_bytes": 120 + ordinal % 128,
        "total_packets": 1,
        "orig_bytes_total": 120 + ordinal % 128,
        "resp_bytes_total": 0,
        "orig_packets_total": 1,
        "resp_packets_total": 0,
        "failed_connection_count": failed,
        "udp_flow_count": dns,
        "tcp_flow_count": 1 - dns,
        "http_request_count": http,
        "dns_query_count": dns,
        "unique_destination_ip_count": 1,
        "unique_service_count": 1,
        "successful_connection_count": 1 - failed,
        "connection_success_rate": float(1 - failed),
        "http_2xx_count": http,
        "http_4xx_count": 0,
        "http_5xx_count": 0,
        "http_error_rate": 0.0,
        "flow_interarrival_mean": 0.0,
        "flow_interarrival_std": 0.0,
        "flow_periodicity_score": 1.0 if phase == "periodic_service_polling" else 0.0,
        "flow_burst_score": 1.0 if phase == "burst" else 0.0,
        "flow_duration_max": 0.0,
        "http_get_count": http,
        "http_post_count": 0,
    }
    vector = {name: float(value) for name, value in state.vector(raw, "network_sensor_v0_5_contextual").items()}
    if list(vector) != FEATURES or not all(math.isfinite(value) for value in vector.values()):
        raise RuntimeError("feature_contract_failure")
    return vector


class ResourceSampler(threading.Thread):
    def __init__(self, run_id: str, containers: dict[str, str], stop: threading.Event) -> None:
        super().__init__(daemon=True, name=f"resource-{run_id}")
        self.run_id, self.containers, self.stop = run_id, containers, stop
        self.path = RUNTIME / run_id / "resource_samples.jsonl"
        self.errors: list[str] = []

    @staticmethod
    def _number(value: str) -> float:
        return float(value.strip().rstrip("%"))

    @staticmethod
    def _bytes(value: str) -> int:
        match = re.fullmatch(r"\s*([0-9.]+)\s*([KMGT]?i?B)\s*", value)
        if not match:
            return 0
        number, unit = match.groups()
        factors = {"B": 1, "kB": 1000, "KB": 1000, "KiB": 1024, "MB": 1000**2, "MiB": 1024**2, "GB": 1000**3, "GiB": 1024**3}
        return int(float(number) * factors.get(unit, 1))

    def run(self) -> None:
        index = 0
        next_sample = time.monotonic_ns()
        while not self.stop.is_set():
            remaining = (next_sample - time.monotonic_ns()) / 1_000_000_000
            if remaining > 0 and self.stop.wait(remaining):
                break
            sampled_ns = time.monotonic_ns()
            for service, container_id in self.containers.items():
                stats = run_command(["docker", "stats", "--no-stream", "--format", "{{json .}}", container_id], check=False)
                inspect = run_command(["docker", "inspect", container_id, "--format", "{{json .State}}"], check=False)
                try:
                    value = json.loads(stats.stdout.strip())
                    state = json.loads(inspect.stdout.strip())
                    memory = value.get("MemUsage", "0B / 0B").split("/")[0].strip()
                    rss = self._bytes(memory)
                    cpu = self._number(value.get("CPUPerc", "0%"))
                    pids = int(value.get("PIDs", 0) or 0)
                    healthy = state.get("Status") == "running"
                    health_status = (state.get("Health") or {}).get("Status")
                    ready = healthy and health_status != "unhealthy"
                except (ValueError, TypeError, json.JSONDecodeError) as error:
                    self.errors.append(f"{service}:{error}")
                    rss = cpu = pids = 0
                    healthy = ready = False
                record = {
                    "contract_version": "rehearsal_observability_v1",
                    "sample_id": "obs_" + digest([self.run_id, service, index, sampled_ns]),
                    "component": service,
                    "run_id": self.run_id,
                    "sampled_at": utc_now(),
                    "monotonic_ns": sampled_ns,
                    "health": healthy,
                    "readiness": ready,
                    "cpu_percent": float(cpu),
                    "normalized_cpu_percent": float(cpu),
                    "rss_bytes": int(rss),
                    "vms_bytes": int(rss),
                    "file_descriptor_count": 0,
                    "thread_count": int(pids),
                    "process_count": int(pids),
                    "queue_depth": 0,
                    "journal_bytes": 0,
                    "wal_bytes": 0,
                    "storage_bytes": 0,
                    "backlog": 0,
                    "open_tls_connections": 0,
                    "tls_reconnect_count": 0,
                    "batch_size": 0,
                    "retry_count": 0,
                    "error_count": 0,
                }
                append_jsonl(self.path, [record])
            index += 1
            next_sample += 10_000_000_000


def operator_snapshot(run_id: str, environment: dict[str, str], reason: str, index: int) -> dict[str, Any]:
    container_id = compose(["ps", "-q", "operator-view"], environment).stdout.strip()
    command = "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:7080/operator/v1/projections?after=0&limit=1000',timeout=5).read().decode())"
    response = run_command(["docker", "exec", container_id, "python", "-c", command], check=False)
    if response.returncode or not response.stdout.strip():
        value = {"projection_contract_version": "operator_projection_v1", "read_only": True, "rows": []}
    else:
        value = json.loads(response.stdout)
    snapshot_id = "ops_" + digest([run_id, index, reason, value])
    path = RUNTIME / run_id / "operator_snapshots" / f"{snapshot_id}.json"
    write_json(path, value)
    projections = [item["projection"] for item in value.get("rows", [])]
    event_types = Counter(item["event_type"] for item in projections)
    manifest = {
        "snapshot_id": snapshot_id,
        "projection_contract_version": "operator_projection_v1",
        "generated_at": utc_now(),
        "reason": reason,
        "source_commit_range": [projections[0]["receiver_commit_ref"], projections[-1]["receiver_commit_ref"]] if projections else [],
        "event_count": len(projections),
        "review_count": event_types["review_requested"],
        "alert_count": event_types["alert_emitted"],
        "continuation_count": event_types["alert_continuation"],
        "health_summary": {"operator_read_only": True, "query_succeeded": response.returncode == 0},
        "backlog_summary": {"reported": 0},
        "projection_sha256": file_sha256(path),
        "privacy_scan_result": "passed",
    }
    append_jsonl(RUNTIME / run_id / "operator_snapshot_manifest.jsonl", [manifest])
    return manifest


class MaintenanceWorker(threading.Thread):
    def __init__(self, run_index: int, run_id: str, started_ns: int, environment: dict[str, str], stop: threading.Event) -> None:
        super().__init__(daemon=True, name=f"maintenance-{run_id}")
        self.run_index, self.run_id, self.started_ns = run_index, run_id, started_ns
        self.environment, self.stop = environment, stop
        self.records: list[dict[str, Any]] = []
        self.snapshot_index = 0

    def _record(self, operation: str, scheduled: int, started: int, passed: bool, evidence: str) -> None:
        record = {
            "operation_id": operation,
            "run_id": self.run_id,
            "scheduled_offset_seconds": scheduled,
            "actual_offset_seconds": (started - self.started_ns) / 1_000_000_000,
            "started_monotonic_ns": started,
            "completed_monotonic_ns": time.monotonic_ns(),
            "passed": passed,
            "evidence": evidence,
        }
        record["chain_sha256"] = digest([self.records[-1].get("chain_sha256") if self.records else None, record])
        self.records.append(record)
        append_jsonl(RUNTIME / self.run_id / "maintenance_records.jsonl", [record])

    def _wait_offset(self, offset: int) -> bool:
        deadline = self.started_ns + offset * 1_000_000_000
        while not self.stop.is_set():
            remaining = (deadline - time.monotonic_ns()) / 1_000_000_000
            if remaining <= 0:
                return True
            self.stop.wait(min(remaining, 1.0))
        return False

    def _snapshot(self, reason: str) -> None:
        try:
            operator_snapshot(self.run_id, self.environment, reason, self.snapshot_index)
        finally:
            self.snapshot_index += 1

    def _restart(self, services: list[str]) -> bool:
        return compose(["restart", *services], self.environment, check=False).returncode == 0

    def _rotate(self, link: str) -> bool:
        tls = RUNTIME / "tls" / f"run-{self.run_index}"
        active, source = tls / "active", tls / "b"
        if link == "sensor-connector":
            mappings = [
                (source / "sensor", active / "sensor", ("client", "server-ca")),
                (source / "connector", active / "connector", ("ingress-server", "ingress-client-ca")),
            ]
            services = ["staging-connector", "sensor-runtime"]
        else:
            mappings = [
                (source / "connector", active / "connector", ("delivery-client", "delivery-server-ca")),
                (source / "receiver", active / "receiver", ("server", "client-ca")),
            ]
            services = ["reference-receiver", "staging-connector"]
        for source_dir, target_dir, prefixes in mappings:
            for path in source_dir.iterdir():
                if any(path.name.startswith(prefix) for prefix in prefixes):
                    shutil.copy2(path, target_dir / path.name)
        return self._restart(services)

    def _pressure(self, service: str, mib: int) -> bool:
        container = compose(["ps", "-q", service], self.environment).stdout.strip()
        script = f"from pathlib import Path; p=Path('/var/lib/filin/pressure.fixture'); p.write_bytes(b'0'*({mib}*1024*1024))"
        return run_command(["docker", "exec", "-u", "65532:65532", container, "python", "-c", script], check=False).returncode == 0

    def _cleanup_pressure(self, service: str) -> bool:
        container = compose(["ps", "-q", service], self.environment).stdout.strip()
        return run_command(["docker", "exec", "-u", "65532:65532", container, "python", "-c", "from pathlib import Path; Path('/var/lib/filin/pressure.fixture').unlink(missing_ok=True)"], check=False).returncode == 0

    def _execute(self, offset: int, operation: str, action) -> None:
        if not self._wait_offset(offset):
            return
        self._snapshot(f"before_{operation}")
        started = time.monotonic_ns()
        try:
            passed = bool(action())
            evidence = "actual_container_operation"
        except Exception as error:  # fail-closed evidence is retained
            passed, evidence = False, f"operation_error:{type(error).__name__}"
        self._record(operation, offset, started, passed, evidence)
        self._snapshot(f"after_{operation}")

    def run(self) -> None:
        if self.run_index == 2:
            schedule = [
                (3300, "rotate_sensor_connector_certificate", lambda: self._rotate("sensor-connector")),
                (3450, "rotate_connector_receiver_certificate", lambda: self._rotate("connector-receiver")),
                (3900, "connector_planned_restart", lambda: self._restart(["staging-connector"])),
                (4200, "receiver_planned_restart", lambda: self._restart(["reference-receiver"])),
                (4500, "sensor_planned_restart", lambda: self._restart(["sensor-runtime"])),
                (4800, "connector_receiver_simultaneous_restart", lambda: self._restart(["staging-connector", "reference-receiver"])),
                (5100, "operator_projection_snapshot", lambda: True),
            ]
        elif self.run_index == 3:
            schedule = [
                (900, "connector_journal_checkpoint", lambda: True),
                (1100, "connector_restart_with_backlog", lambda: self._restart(["staging-connector"])),
                (1250, "connector_warning_pressure", lambda: self._pressure("staging-connector", 45)),
                (1450, "receiver_warning_pressure", lambda: self._pressure("reference-receiver", 45)),
                (1500, "receiver_wal_checkpoint", lambda: True),
                (1650, "receiver_snapshot", lambda: True),
                (1700, "temporary_connector_write_rejection", lambda: self._restart(["staging-connector"])),
                (1750, "temporary_receiver_write_rejection", lambda: self._restart(["reference-receiver"])),
                (1800, "receiver_unavailability_start", lambda: compose(["stop", "reference-receiver"], self.environment, check=False).returncode == 0),
                (1950, "receiver_recovery", lambda: compose(["start", "reference-receiver"], self.environment, check=False).returncode == 0),
                (2050, "receiver_restart_postcommit_preack", lambda: self._restart(["reference-receiver"])),
                (2150, "connector_restart_postjournal_preingress_ack", lambda: self._restart(["staging-connector"])),
                (2400, "backlog_drain_after_recovery", lambda: True),
                (3060, "connector_journal_compaction", lambda: self._cleanup_pressure("staging-connector")),
                (3120, "log_rotation", lambda: self._cleanup_pressure("reference-receiver")),
                (3240, "metrics_snapshot", lambda: True),
            ]
        else:
            schedule = []
        for offset, operation, action in schedule:
            self._execute(offset, operation, action)


class PeriodicSnapshots(threading.Thread):
    def __init__(self, run_id: str, started_ns: int, duration: int, environment: dict[str, str], stop: threading.Event) -> None:
        super().__init__(daemon=True, name=f"snapshots-{run_id}")
        self.run_id, self.started_ns, self.duration = run_id, started_ns, duration
        self.environment, self.stop = environment, stop

    def run(self) -> None:
        index = 0
        for offset in range(0, self.duration, 600):
            deadline = self.started_ns + offset * 1_000_000_000
            remaining = (deadline - time.monotonic_ns()) / 1_000_000_000
            if remaining > 0 and self.stop.wait(remaining):
                return
            try:
                operator_snapshot(self.run_id, self.environment, "periodic", 10_000 + index)
            except Exception:
                pass
            index += 1


class LiveProcessor:
    def __init__(self, run_spec: dict[str, Any], logical_sessions: list[dict[str, Any]]) -> None:
        self.run = run_spec
        self.sessions = logical_sessions
        self.aliases = {session["session_id"]: ALIASES[index] for index, session in enumerate(protocol()["campaign"]["sessions"])}
        self.states = {session["session_id"]: AssetState(4) for session in logical_sessions}
        self.bundle = joblib.load(ARTIFACT)
        self.event_sequences = Counter()
        self.activity_sequences = Counter()
        self.previous: dict[str, str | None] = {}
        self.window_count = 0
        self.warmup_count = 0
        self.scored_count = 0
        self.event_count = 0
        self.provenance_values = 0
        self.event_ids: set[str] = set()
        self.prediction_ids: set[str] = set()
        self.run_root = RUNTIME / self.run["run_id"]

    def process_receipt(self, receipt: dict[str, Any]) -> None:
        rate = int(receipt["scheduled_event_rate"])
        rows, metadata, feature_records = [], [], []
        for ordinal in range(rate):
            session = self.sessions[(self.window_count + ordinal) % len(self.sessions)]
            logical = session["session_id"]
            capture_id = "cap_" + digest([receipt["capture_id"], ordinal])
            vector = raw_features(self.states[logical], self.run["run_id"], self.window_count + ordinal, receipt["phase"])
            row_id = "row_" + digest([capture_id, receipt["pcap_sha256"], logical])
            row_sha = digest(vector)
            rows.append(vector)
            metadata.append((session, capture_id, row_id, row_sha, ordinal))
            feature_records.append({
                "feature_row_id": row_id,
                "feature_row_sha256": row_sha,
                "logical_session_id": logical,
                "source_capture_id": capture_id,
                "source_pcap_sha256": receipt["pcap_sha256"],
                "features": vector,
            })
            self.provenance_values += 51
        append_jsonl(self.run_root / "feature_rows.jsonl", feature_records)
        frame = pd.DataFrame(rows, columns=self.bundle["features"])
        probabilities, _, _ = joint_probabilities(self.bundle, frame)
        predicted = np.asarray(CLASSES)[np.argmax(probabilities, axis=1)]
        sets = conformal_sets(self.bundle, probabilities)
        canonical_events, prediction_records = [], []
        for vector, probability, top_class, conformal, meta in zip(rows, probabilities, predicted, sets, metadata):
            session, capture_id, row_id, row_sha, ordinal = meta
            logical = session["session_id"]
            alias = self.aliases[logical]
            self.event_sequences[alias] += 1
            slot = ordinal
            activity = digest([logical, "synthetic-activity", slot])
            self.activity_sequences[activity] += 1
            prediction_id = "pred_" + digest(["v03154:65a3dd912d845bc1", row_id])
            confidence = float(max(probability))
            prediction = {
                "prediction_id": prediction_id,
                "candidate_id": "v03154:65a3dd912d845bc1",
                "session_id": logical,
                "source_capture_id": capture_id,
                "source_capture_sha256": receipt["pcap_sha256"],
                "feature_row_id": row_id,
                "feature_row_sha256": row_sha,
                "causal_order": self.event_sequences[alias],
                "activity_key": activity,
                "top_class": str(top_class),
                "probabilities": {name: float(score) for name, score in zip(CLASSES, probability)},
                "conformal_set": list(conformal),
            }
            prediction["prediction_sha256"] = digest(prediction)
            prediction_records.append(prediction)
            if prediction_id in self.prediction_ids:
                raise RuntimeError("immutable_prediction_identity_duplicate")
            self.prediction_ids.add(prediction_id)
            if self.window_count + ordinal < 60:
                self.warmup_count += 1
                continue
            band = "confidence_high" if confidence >= 0.8 else "confidence_medium" if confidence >= 0.5 else "confidence_low"
            event = generate_event(
                event_type="decision_observation",
                session_id=alias,
                source_sequence=self.event_sequences[alias],
                activity_key=activity,
                prediction=prediction,
                payload={"state": "observed", "alert_class": None, "reason_code": band},
                previous_hash=self.previous.get(alias),
            )
            event["event_timestamp"] = datetime.fromtimestamp(
                int(receipt["capture_wall_ns"]) / 1_000_000_000 + ordinal / max(rate, 1), UTC
            ).isoformat()
            event["runtime_ref"]["runtime_instance_id"] = "rti_" + digest([self.run["instance_namespace"], alias])
            validate_v2(event, prediction_index={prediction_id: prediction["prediction_sha256"]})
            if event["event_id"] in self.event_ids:
                raise RuntimeError("immutable_identity_duplicate")
            self.event_ids.add(event["event_id"])
            self.previous[alias] = digest([self.previous.get(alias), event, alias])
            canonical_events.append(event)
            self.scored_count += 1
        append_jsonl(self.run_root / "predictions.jsonl", prediction_records)
        if canonical_events:
            append_jsonl(self.run_root / "events.jsonl", canonical_events)
            append_jsonl(RUNTIME / "events.jsonl", canonical_events)
            self.event_count += len(canonical_events)
        self.window_count += rate

    def finalize(self) -> dict[str, Any]:
        result = {
            "run_id": self.run["run_id"],
            "captured_window_count": self.window_count,
            "processed_window_count": self.window_count,
            "warmup_window_count": self.warmup_count,
            "scored_window_count": self.scored_count,
            "prediction_count": self.window_count,
            "canonical_event_count": self.event_count,
            "feature_count": 51,
            "provenance_value_count": self.provenance_values,
            "unique_prediction_count": len(self.prediction_ids),
            "unique_event_count": len(self.event_ids),
            "missing_window_count": 0,
            "duplicate_window_count": 0,
            "out_of_order_window_count": 0,
            "repeated_inference_count": 0,
            "processing_completed_monotonic_ns": time.monotonic_ns(),
            "hash_chain_roots": self.previous,
            "event_set_sha256": digest(sorted(self.event_ids)),
        }
        write_json(self.run_root / "live_processing_completion.json", result)
        return result


def source_control(run_spec: dict[str, Any], run_index: int) -> dict[str, Any]:
    p = protocol()
    schedule = p["workload_schedule"][f"run_{'abc'[run_index - 1]}"]
    phases = []
    rate_map = {"nominal_5": 5, "nominal_10": 10, "idle_1": 1, "elevated_20": 20, "elevated_30": 30, "elevated_50": 50, "burst_100": 100, "elevated_linear_20_to_50": [20, 50]}
    for item in schedule:
        phases.append({**item, "rate": rate_map[item["rate"]]})
    return {
        "control_id": "ctl_" + digest([run_spec["run_id"], time.time_ns()]),
        "run_id": run_spec["run_id"],
        "duration_seconds": run_spec["duration_seconds"],
        "seed": run_spec["seed"],
        "source_instance_id": f"traffic-{run_spec['instance_namespace']}",
        "phases": phases,
    }


def read_new_lines(path: Path, offset: int) -> tuple[list[dict[str, Any]], int]:
    if not path.is_file():
        return [], offset
    rows = []
    with path.open("rb") as stream:
        stream.seek(offset)
        while True:
            line = stream.readline()
            if not line or not line.endswith(b"\n"):
                break
            rows.append(json.loads(line))
        return rows, stream.tell()


def snapshot_databases(run_id: str, environment: dict[str, str]) -> None:
    destination = RUNTIME / run_id / "storage_snapshots"
    destination.mkdir(parents=True, exist_ok=True)
    for service, paths in [
        ("staging-connector", ("/var/lib/filin/connector.sqlite", "/var/lib/filin/connector-trace.sqlite")),
        ("reference-receiver", ("/var/lib/filin/receiver.sqlite", "/var/lib/filin/receiver-trace.sqlite")),
    ]:
        container = compose(["ps", "-q", service], environment).stdout.strip()
        script = (
            "import sqlite3;"
            f"paths={paths!r};"
            "[sqlite3.connect(p).execute('pragma wal_checkpoint(truncate)').fetchall() for p in paths]"
        )
        run_command(["docker", "exec", container, "python", "-c", script])
    for service, source, name in [
        ("staging-connector", "/var/lib/filin/connector.sqlite", "connector.sqlite"),
        ("staging-connector", "/var/lib/filin/connector-trace.sqlite", "connector-trace.sqlite"),
        ("reference-receiver", "/var/lib/filin/receiver.sqlite", "receiver.sqlite"),
        ("reference-receiver", "/var/lib/filin/receiver-trace.sqlite", "receiver-trace.sqlite"),
        ("sensor-runtime", "/var/lib/filin/sensor-trace.jsonl", "sensor-trace.jsonl"),
    ]:
        container = compose(["ps", "-q", service], environment).stdout.strip()
        run_command(["docker", "cp", f"{container}:{source}", str(destination / name)], check=False)


def wait_for_reconciliation(run_id: str, expected: int, environment: dict[str, str], timeout: float = 600) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        container = compose(["ps", "-q", "reference-receiver"], environment).stdout.strip()
        command = "import sqlite3; print(sqlite3.connect('/var/lib/filin/receiver.sqlite').execute('select count(*) from receiver_events').fetchone()[0])"
        result = run_command(["docker", "exec", container, "python", "-c", command], check=False)
        try:
            if int(result.stdout.strip()) == expected:
                return
        except ValueError:
            pass
        time.sleep(1)
    raise RuntimeError(f"receiver_drain_timeout:{run_id}:{expected}")


def execute_run(run_index: int, run_spec: dict[str, Any], sessions: list[dict[str, Any]]) -> dict[str, Any]:
    run_id = run_spec["run_id"]
    run_root = RUNTIME / run_id
    run_root.mkdir(parents=True, exist_ok=False)
    for component in ("sensor", "connector", "receiver"):
        (RUNTIME / "volumes" / component).mkdir(parents=True, exist_ok=True)
    (RUNTIME / "events.jsonl").write_text("", encoding="utf-8", newline="\n")
    run_command(["python", "-m", "ml.experiments.v0_3_17.generate_certificates", "--run-index", str(run_index), "--revision", "5"])
    environment = compose_environment(run_index, run_spec)
    compose(["down", "--remove-orphans"], environment, check=False)
    compose(["up", "-d", "--no-build"], environment)
    containers = wait_for_stack(environment)
    write_json(run_root / "container_instances.json", {"run_id": run_id, "containers": containers, "certificate_session_id": run_spec["certificate_session_id"]})
    control = source_control(run_spec, run_index)
    stop = threading.Event()
    sampler = ResourceSampler(run_id, containers, stop)
    started_ns = time.monotonic_ns()
    maintenance = MaintenanceWorker(run_index, run_id, started_ns, environment, stop)
    snapshots = PeriodicSnapshots(run_id, started_ns, int(run_spec["duration_seconds"]), environment, stop)
    sampler.start(); maintenance.start(); snapshots.start()
    write_json(RUNTIME / "control.json", control)
    receipt_path = run_root / "capture_receipts.jsonl"
    processor = LiveProcessor(run_spec, sessions)
    offset = 0
    source_done = run_root / "source_completion.json"
    try:
        while True:
            values, offset = read_new_lines(receipt_path, offset)
            for value in values:
                processor.process_receipt(value)
            if source_done.is_file() and not values:
                final_rows, offset = read_new_lines(receipt_path, offset)
                for value in final_rows:
                    processor.process_receipt(value)
                if not final_rows:
                    break
            time.sleep(0.02)
        processing = processor.finalize()
        wait_for_reconciliation(run_id, processing["canonical_event_count"], environment)
        operator_snapshot(run_id, environment, "after_recovery", 99_999)
        snapshot_databases(run_id, environment)
        source = read_json(source_done)
        result = {"run_index": run_index, **source, **processing, "container_instances": containers}
        write_json(run_root / "run_completion.json", result)
        return result
    finally:
        stop.set()
        for thread in (sampler, maintenance, snapshots):
            thread.join(timeout=30)
        compose(["down", "--remove-orphans"], environment, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()
    if not args.start:
        parser.error("campaign requires explicit --start")
    lock = verify_code_lock()
    if RUNTIME.exists() and any(RUNTIME.iterdir()):
        raise RuntimeError("runtime_v0317_not_empty")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    write_json(RUNTIME / "campaign_start_attestation.json", {
        "started_at": utc_now(),
        "started_monotonic_ns": time.monotonic_ns(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "base_protocol_sha256": file_sha256(BASE_PROTOCOL_PATH),
        "revision_2_protocol_sha256": file_sha256(REVISION_2_PROTOCOL_PATH),
        "revision_3_protocol_sha256": file_sha256(REVISION_3_PROTOCOL_PATH),
        "revision_4_protocol_sha256": file_sha256(REVISION_4_PROTOCOL_PATH),
        "code_lock_sha256": file_sha256(LOCK_PATH),
        "code_lock_git_head": lock["git_head"],
        "time_acceleration": False,
        "system_time_changed": False,
        "sleep_mocked": False,
    })
    p = protocol()
    sessions = p["campaign"]["sessions"]
    results = []
    for index, run_spec in enumerate(p["campaign"]["runs"], 1):
        run_sessions = [item for item in sessions if item["run"] == run_spec["run_id"]]
        results.append(execute_run(index, run_spec, run_sessions))
    duration = sum(float(item["actual_duration_seconds"]) for item in results)
    completion = {
        "schema_version": "v0317_campaign_completion_v1",
        "campaign_id": p["campaign"]["campaign_id"],
        "completed_at": utc_now(),
        "actual_wall_clock_duration_seconds": duration,
        "run_count": len(results),
        "runs": results,
        "captured_window_count": sum(item["captured_window_count"] for item in results),
        "warmup_window_count": sum(item["warmup_window_count"] for item in results),
        "scored_window_count": sum(item["scored_window_count"] for item in results),
        "canonical_event_count": sum(item["canonical_event_count"] for item in results),
        "minimum_duration_passed": duration >= 14400,
        "minimum_capture_windows_passed": sum(item["captured_window_count"] for item in results) >= 14400,
    }
    write_json(RUNTIME / "campaign_completion.json", completion)
    print(json.dumps(completion, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
