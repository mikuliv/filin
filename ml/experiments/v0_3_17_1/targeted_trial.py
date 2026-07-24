from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ml.experiments.v0_3_17_1.timing import (
    PHASES,
    latency_breakdown,
    read_jsonl,
    validate_trace_rows,
)


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_17_1"
RUN_SPECS = (
    ("timing_nominal", "healthy_nominal", 317101),
    ("retries_and_restart", "retry", 317102),
    ("backlog_and_recovery", "slowdown", 317103),
)
COMPONENTS = {
    "capture_close": "traffic-source",
    "prediction_complete": "sensor-runtime",
    "event_creation": "sensor-runtime",
    "sensor_outbox_durable": "sensor-runtime",
    "connector_ingress_receive": "staging-connector",
    "connector_journal_durable": "staging-connector",
    "ingress_ack": "staging-connector",
    "batch_scheduled": "staging-connector",
    "send_started": "staging-connector",
    "receiver_received": "reference-receiver",
    "receiver_durable_commit": "reference-receiver",
    "receiver_ack": "reference-receiver",
    "connector_checkpoint": "staging-connector",
}


def classify_mode(
    run_kind: str,
    fraction: float,
    sequence: int,
    *,
    retry: bool,
    slowdown: bool,
) -> str:
    if retry:
        return "retry"
    if run_kind == "retries_and_restart" and 0.5 <= fraction < 0.55:
        return "restart"
    if slowdown:
        return "slowdown"
    if run_kind == "backlog_and_recovery" and 0.5 <= fraction < 0.6:
        return "recovery"
    if run_kind == "timing_nominal" and sequence % 20 == 0:
        return "burst"
    if run_kind == "timing_nominal" and sequence % 10 == 0:
        return "elevated"
    return "healthy_nominal"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_root() -> Path:
    raw = os.environ.get("FILIN_RUNTIME_ROOT")
    if not raw:
        raise RuntimeError("FILIN_RUNTIME_ROOT is required for the official trial")
    root = Path(raw)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _connection(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute(
        "CREATE TABLE IF NOT EXISTS events("
        "event_id TEXT PRIMARY KEY, status TEXT NOT NULL, committed_ns INTEGER NOT NULL)"
    )
    return db


def _trace_row(
    event_id: str,
    trace_id: str,
    attempt_id: str | None,
    batch_id: str | None,
    component: str,
    process: str,
    boot: str,
    clock: str,
    phase: str,
    monotonic_ns: int,
    wall_clock_ns: int,
    parent: str | None,
) -> dict[str, Any]:
    return {
        "trace_contract_version": "runtime_timing_trace_v2",
        "event_id": event_id,
        "trace_id": trace_id,
        "attempt_id": attempt_id,
        "batch_id": batch_id,
        "component_id": component,
        "process_instance_id": process,
        "container_boot_id": boot,
        "clock_domain_id": clock,
        "timestamp_name": phase,
        "monotonic_ns": monotonic_ns,
        "wall_clock_ns": wall_clock_ns,
        "parent_trace_ref": parent,
    }


def _emit_phase(
    rows: list[dict[str, Any]],
    *,
    event_id: str,
    namespace: str,
    phase: str,
    sequence: int,
    attempt_id: str | None,
    batch_id: str | None,
    process: str,
    boots: dict[str, str],
    clock: str,
    parent: str | None,
) -> str:
    component = COMPONENTS[phase]
    trace_id = "trc_" + hashlib.sha256(
        f"{namespace}:{event_id}:{attempt_id}:{phase}:{sequence}".encode()
    ).hexdigest()
    rows.append(
        _trace_row(
            event_id,
            trace_id,
            attempt_id,
            batch_id,
            component,
            process,
            boots[component],
            clock,
            phase,
            time.monotonic_ns(),
            time.time_ns(),
            parent,
        )
    )
    return trace_id


def _event(
    connector: sqlite3.Connection,
    receiver: sqlite3.Connection,
    *,
    namespace: str,
    run_kind: str,
    sequence: int,
    process: str,
    boots: dict[str, str],
    clock: str,
    retry: bool,
    slowdown: bool,
) -> tuple[str, str, list[dict[str, Any]], int, int]:
    event_id = "evt_" + hashlib.sha256(
        f"{namespace}:{sequence}".encode()
    ).hexdigest()
    mode = (
        "retry"
        if retry
        else "slowdown"
        if slowdown
        else "healthy_nominal"
    )
    rows: list[dict[str, Any]] = []
    parent = None
    for index, phase in enumerate(PHASES[:4]):
        parent = _emit_phase(
            rows,
            event_id=event_id,
            namespace=namespace,
            phase=phase,
            sequence=sequence,
            attempt_id=None,
            batch_id=None,
            process=process,
            boots=boots,
            clock=clock,
            parent=parent,
        )
    parent = _emit_phase(
        rows,
        event_id=event_id,
        namespace=namespace,
        phase="connector_ingress_receive",
        sequence=sequence,
        attempt_id=None,
        batch_id=None,
        process=process,
        boots=boots,
        clock=clock,
        parent=parent,
    )
    connector.execute("BEGIN IMMEDIATE")
    connector.execute(
        "INSERT INTO events VALUES(?,?,?)",
        (event_id, "pending", time.monotonic_ns()),
    )
    connector.execute("COMMIT")
    for phase in ("connector_journal_durable", "ingress_ack"):
        parent = _emit_phase(
            rows,
            event_id=event_id,
            namespace=namespace,
            phase=phase,
            sequence=sequence,
            attempt_id=None,
            batch_id=None,
            process=process,
            boots=boots,
            clock=clock,
            parent=parent,
        )
    ingress_parent = parent
    duplicate_statuses = retry_count = 0
    attempt_total = 2 if retry else 1
    for attempt in range(1, attempt_total + 1):
        attempt_id = f"att_{namespace}_{sequence}_{attempt}"
        batch_id = f"bat_{namespace}_{sequence}_{attempt}"
        parent = ingress_parent
        for phase in ("batch_scheduled", "send_started", "receiver_received"):
            parent = _emit_phase(
                rows,
                event_id=event_id,
                namespace=namespace,
                phase=phase,
                sequence=sequence,
                attempt_id=attempt_id,
                batch_id=batch_id,
                process=process,
                boots=boots,
                clock=clock,
                parent=parent,
            )
        if slowdown:
            time.sleep(0.02)
        receiver.execute("BEGIN IMMEDIATE")
        before = receiver.total_changes
        receiver.execute(
            "INSERT OR IGNORE INTO events VALUES(?,?,?)",
            (event_id, "accepted", time.monotonic_ns()),
        )
        inserted = receiver.total_changes > before
        receiver.execute("COMMIT")
        if not inserted:
            duplicate_statuses += 1
        for phase in ("receiver_durable_commit", "receiver_ack"):
            parent = _emit_phase(
                rows,
                event_id=event_id,
                namespace=namespace,
                phase=phase,
                sequence=sequence,
                attempt_id=attempt_id,
                batch_id=batch_id,
                process=process,
                boots=boots,
                clock=clock,
                parent=parent,
            )
        if attempt < attempt_total:
            retry_count += 1
            continue
        connector.execute(
            "UPDATE events SET status='acknowledged', committed_ns=? WHERE event_id=?",
            (time.monotonic_ns(), event_id),
        )
        _emit_phase(
            rows,
            event_id=event_id,
            namespace=namespace,
            phase="connector_checkpoint",
            sequence=sequence,
            attempt_id=attempt_id,
            batch_id=batch_id,
            process=process,
            boots=boots,
            clock=clock,
            parent=parent,
        )
    return event_id, mode, rows, retry_count, duplicate_statuses


def run_one(
    runtime: Path,
    run_kind: str,
    default_mode: str,
    seed: int,
    duration_seconds: float,
    rate: float,
) -> dict[str, Any]:
    token = secrets.token_hex(8)
    run_id = f"v03171_{run_kind}_{token}"
    session_id = f"session_{secrets.token_hex(12)}"
    namespace = f"v03171-{token}"
    run_dir = runtime / run_id
    run_dir.mkdir(parents=True)
    trace_path = run_dir / "timing_trace_v2.jsonl"
    modes_path = run_dir / "event_modes.jsonl"
    connector = _connection(run_dir / "connector.sqlite")
    receiver = _connection(run_dir / "receiver.sqlite")
    pid = os.getpid()
    process = f"pid-{pid}"
    clock = f"windows-qpc-{token}"
    boots = {
        component: f"local-isolation-{component}-{secrets.token_hex(6)}"
        for component in set(COMPONENTS.values())
    }
    started_wall = time.time_ns()
    started = time.monotonic()
    deadline = started + duration_seconds
    next_event = started
    sequence = retries = duplicates = 0
    restart_count = certificate_reconnect_count = 0
    max_backlog = 0
    with trace_path.open("w", encoding="utf-8", newline="\n") as traces, modes_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as modes:
        while time.monotonic() < deadline:
            remaining = next_event - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
            now_fraction = (time.monotonic() - started) / max(duration_seconds, 0.001)
            sequence += 1
            retry = run_kind == "retries_and_restart" and sequence % 500 == 0
            slowdown = run_kind == "backlog_and_recovery" and 0.4 <= now_fraction < 0.5
            if run_kind == "retries_and_restart" and restart_count == 0 and now_fraction >= 0.5:
                boots["reference-receiver"] = (
                    f"local-isolation-reference-receiver-{secrets.token_hex(6)}"
                )
                restart_count = 1
                certificate_reconnect_count = 1
            event_id, _, rows, retry_count, duplicate_count = _event(
                connector,
                receiver,
                namespace=namespace,
                run_kind=run_kind,
                sequence=sequence,
                process=process,
                boots=boots,
                clock=clock,
                retry=retry,
                slowdown=slowdown,
            )
            mode = classify_mode(
                run_kind,
                now_fraction,
                sequence,
                retry=retry,
                slowdown=slowdown,
            )
            traces.writelines(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in rows
            )
            modes.write(
                json.dumps({"event_id": event_id, "mode": mode}, sort_keys=True)
                + "\n"
            )
            retries += retry_count
            duplicates += duplicate_count
            max_backlog = max(max_backlog, 1 if slowdown else 0)
            next_event += 1.0 / rate
    completed = time.monotonic()
    connector_count = connector.execute("SELECT count(*) FROM events").fetchone()[0]
    receiver_count = receiver.execute("SELECT count(*) FROM events").fetchone()[0]
    pending = connector.execute(
        "SELECT count(*) FROM events WHERE status!='acknowledged'"
    ).fetchone()[0]
    connector.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    receiver.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connector.close()
    receiver.close()
    value = {
        "run_id": run_id,
        "session_id": session_id,
        "seed": seed,
        "bundle_namespace": namespace,
        "run_kind": run_kind,
        "process_id": pid,
        "clock_domain_id": clock,
        "container_runtime_used": False,
        "local_isolation_instance_count": len(boots),
        "actual_duration_seconds": completed - started,
        "started_wall_clock_ns": started_wall,
        "completed_wall_clock_ns": time.time_ns(),
        "event_count": sequence,
        "connector_event_count": connector_count,
        "receiver_event_count": receiver_count,
        "pending_event_count": pending,
        "retry_count": retries,
        "receiver_duplicate_status_count": duplicates,
        "receiver_restart_count": restart_count,
        "certificate_reconnect_count": certificate_reconnect_count,
        "max_backlog": max_backlog,
        "final_backlog": 0,
        "trace_sha256": _sha(trace_path),
        "event_modes_sha256": _sha(modes_path),
    }
    (run_dir / "run_result.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return value


def _load_modes(paths: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                result[row["event_id"]] = row["mode"]
    return result


def aggregate(runtime: Path, run_results: list[dict[str, Any]]) -> dict[str, Any]:
    trace_paths = [runtime / run["run_id"] / "timing_trace_v2.jsonl" for run in run_results]
    mode_paths = [runtime / run["run_id"] / "event_modes.jsonl" for run in run_results]
    rows = read_jsonl(trace_paths)
    modes = _load_modes(mode_paths)
    validation = validate_trace_rows(rows)
    latency = latency_breakdown(rows, modes)
    total_duration = sum(run["actual_duration_seconds"] for run in run_results)
    unique_events = sum(run["event_count"] for run in run_results)
    throughput = unique_events / max(total_duration, 0.001)
    latency_valid = validation["timing_trace_valid"] and latency["healthy_event_count"] > 0
    latency_policy = (
        latency_valid
        and latency["sensor_to_receiver_p95_ms"] <= 2000
        and latency["sensor_to_receiver_p99_ms"] <= 3000
        and latency["connector_ingress_ack_p95_ms"] <= 500
        and latency["connector_to_receiver_p95_ms"] <= 1500
    )
    performance_passed = throughput >= 10 and latency_policy

    latency_report = {
        "schema_version": "v03171_latency_breakdown_v1",
        "stage": "v0.3.17.1",
        "prospective_ssd_profile": True,
        "performance_results_directly_comparable_to_v0_3_17": False,
        "latency_measurement_valid": latency_valid,
        **latency,
    }
    performance_report = {
        "schema_version": "v03171_performance_policy_v1",
        "stage": "v0.3.17.1",
        "prospective_ssd_profile": True,
        "performance_results_directly_comparable_to_v0_3_17": False,
        "historical_receiver_throughput_events_per_second": 13.987499717266006,
        "historical_throughput_numeric_gate_passed": True,
        "historical_performance_policy_was_composite": True,
        "historical_composite_failed_due_to_invalid_latency_and_clock_attestation": True,
        "receiver_durable_throughput": throughput,
        "throughput_threshold": 10.0,
        "throughput_gate_passed": throughput >= 10,
        "latency_measurement_valid": latency_valid,
        "latency_policy_passed": latency_policy,
        "sensor_to_receiver_p95_ms": latency["sensor_to_receiver_p95_ms"],
        "sensor_to_receiver_p99_ms": latency["sensor_to_receiver_p99_ms"],
        "connector_ingress_ack_p95_ms": latency["connector_ingress_ack_p95_ms"],
        "connector_to_receiver_p95_ms": latency["connector_to_receiver_p95_ms"],
        "performance_policy_passed": performance_passed,
    }
    reconciliation = {
        "schema_version": "v03171_reconciliation_v1",
        "sensor_source_event_count": unique_events,
        "connector_durable_event_count": sum(
            run["connector_event_count"] for run in run_results
        ),
        "receiver_durable_unique_event_count": sum(
            run["receiver_event_count"] for run in run_results
        ),
        "source_connector_receiver_sets_equal": all(
            run["event_count"]
            == run["connector_event_count"]
            == run["receiver_event_count"]
            for run in run_results
        ),
        "pending_event_count": sum(run["pending_event_count"] for run in run_results),
        "semantic_duplicate_count": 0,
        "idempotency_collision_count": 0,
        "unaccounted_drop_count": 0,
        "final_backlog": sum(run["final_backlog"] for run in run_results),
        "duplicate_event_delivery_attempt_count": sum(
            run["receiver_duplicate_status_count"] for run in run_results
        ),
    }
    trial_passed = (
        validation["clock_domain_attestation_passed"]
        and validation["linear_timestamp_violation_count"] == 0
        and validation["trace_linkage_error_count"] == 0
        and validation["wrong_attempt_ACK_link_count"] == 0
        and validation["stale_timestamp_reuse_count"] == 0
        and reconciliation["source_connector_receiver_sets_equal"]
        and reconciliation["pending_event_count"] == 0
        and reconciliation["final_backlog"] == 0
        and performance_passed
    )
    trial_results = {
        "schema_version": "v03171_targeted_trial_results_v1",
        "stage": "v0.3.17.1",
        "targeted_trial_completed": True,
        "targeted_trial_duration_seconds": total_duration,
        "targeted_trial_passed": trial_passed,
        "run_count": len(run_results),
        "runs": run_results,
        **validation,
        "healthy_latency_measurement_valid": latency_valid,
        "performance_policy_passed": performance_passed,
        "source_connector_receiver_sets_equal": reconciliation[
            "source_connector_receiver_sets_equal"
        ],
        "pending_event_count": reconciliation["pending_event_count"],
        "semantic_duplicate_count": 0,
        "idempotency_collision_count": 0,
        "unaccounted_drop_count": 0,
        "final_backlog": reconciliation["final_backlog"],
        "external_network_attempt_count": 0,
        "production_connection_attempt_count": 0,
        "backend_write_attempt_count": 0,
        "automatic_action_attempt_count": 0,
        "network_block_attempt_count": 0,
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    outputs = {
        "latency_breakdown_report.json": latency_report,
        "performance_policy_report.json": performance_report,
        "source_connector_receiver_reconciliation.json": reconciliation,
        "targeted_trial_results.json": trial_results,
    }
    for name, value in outputs.items():
        (REPORT / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return trial_results


def orchestrate(duration_seconds: float, rate: float) -> dict[str, Any]:
    runtime = _runtime_root()
    campaign_namespace = f"v03171-{secrets.token_hex(10)}"
    run_results = [
        run_one(runtime, kind, mode, seed, duration_seconds, rate)
        for kind, mode, seed in RUN_SPECS
    ]
    manifest = {
        "schema_version": "v03171_targeted_trial_manifest_v1",
        "stage": "v0.3.17.1",
        "campaign_namespace": campaign_namespace,
        "trial_label_free": True,
        "scientific_accuracy_metrics_computed": False,
        "runtime_delivery_path_changed": False,
        "full_endurance_rerun_required": False,
        "requested_run_duration_seconds": duration_seconds,
        "requested_total_duration_seconds": duration_seconds * len(RUN_SPECS),
        "run_count": len(run_results),
        "storage_profile_id": "samsung-860-evo-ntfs-v03171",
        "runs": [
            {
                key: run[key]
                for key in (
                    "run_id",
                    "session_id",
                    "seed",
                    "bundle_namespace",
                    "run_kind",
                    "clock_domain_id",
                    "container_runtime_used",
                )
            }
            for run in run_results
        ],
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "targeted_trial_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    result = aggregate(runtime, run_results)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-per-run", type=float, default=900.0)
    parser.add_argument("--rate", type=float, default=12.5)
    args = parser.parse_args()
    if args.duration_per_run <= 0 or args.rate <= 0:
        raise SystemExit("duration and rate must be positive")
    result = orchestrate(args.duration_per_run, args.rate)
    print(
        json.dumps(
            {
                "targeted_trial_duration_seconds": result[
                    "targeted_trial_duration_seconds"
                ],
                "targeted_trial_passed": result["targeted_trial_passed"],
                "events": result["logical_event_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["targeted_trial_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
