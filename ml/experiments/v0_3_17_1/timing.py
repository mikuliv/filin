from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


TRACE_CONTRACT_VERSION = "runtime_timing_trace_v2"
PHASES = (
    "capture_close",
    "prediction_complete",
    "event_creation",
    "sensor_outbox_durable",
    "connector_ingress_receive",
    "connector_journal_durable",
    "ingress_ack",
    "batch_scheduled",
    "send_started",
    "receiver_received",
    "receiver_durable_commit",
    "receiver_ack",
    "connector_checkpoint",
)
REQUIRED_FIELDS = {
    "trace_contract_version",
    "event_id",
    "trace_id",
    "attempt_id",
    "batch_id",
    "component_id",
    "process_instance_id",
    "container_boot_id",
    "clock_domain_id",
    "timestamp_name",
    "monotonic_ns",
    "wall_clock_ns",
    "parent_trace_ref",
}
TRANSPORT_PHASES = set(PHASES[7:])


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def read_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            rows.extend(json.loads(line) for line in stream if line.strip())
    return rows


def validate_trace_rows(
    rows: list[dict[str, Any]],
    attested_clock_pairs: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    attested = attested_clock_pairs or set()
    by_trace: dict[str, dict[str, Any]] = {}
    errors: Counter[str] = Counter()
    event_ids: set[str] = set()
    for row in rows:
        if set(row) != REQUIRED_FIELDS:
            errors["schema_field_error"] += 1
            continue
        if row["trace_contract_version"] != TRACE_CONTRACT_VERSION:
            errors["contract_version_error"] += 1
        if row["timestamp_name"] not in PHASES:
            errors["timestamp_name_error"] += 1
        if not isinstance(row["monotonic_ns"], int) or row["monotonic_ns"] < 0:
            errors["monotonic_value_error"] += 1
        if not isinstance(row["wall_clock_ns"], int) or row["wall_clock_ns"] < 0:
            errors["wall_clock_value_error"] += 1
        if row["timestamp_name"] in TRANSPORT_PHASES and (
            not row["attempt_id"] or not row["batch_id"]
        ):
            errors["transport_identity_error"] += 1
        if row["trace_id"] in by_trace:
            errors["stale_timestamp_reuse"] += 1
        else:
            by_trace[row["trace_id"]] = row
        event_ids.add(row["event_id"])

    wrong_attempt = wrong_batch = linkage = linear = clock = 0
    for row in by_trace.values():
        parent_ref = row["parent_trace_ref"]
        if parent_ref is None:
            if row["timestamp_name"] != "capture_close":
                linkage += 1
            continue
        parent = by_trace.get(parent_ref)
        if parent is None or parent["event_id"] != row["event_id"]:
            linkage += 1
            continue
        if row["timestamp_name"] in TRANSPORT_PHASES and parent["timestamp_name"] in TRANSPORT_PHASES:
            if row["attempt_id"] != parent["attempt_id"]:
                wrong_attempt += 1
            if row["batch_id"] != parent["batch_id"]:
                wrong_batch += 1
        clock_pair = (parent["clock_domain_id"], row["clock_domain_id"])
        comparable = (
            clock_pair[0] == clock_pair[1]
            or clock_pair in attested
            or (clock_pair[1], clock_pair[0]) in attested
        )
        if not comparable:
            clock += 1
        elif row["monotonic_ns"] < parent["monotonic_ns"]:
            linear += 1
        if row["wall_clock_ns"] < parent["wall_clock_ns"]:
            errors["wall_clock_order_error"] += 1

    errors["trace_linkage_error"] += linkage
    errors["wrong_attempt_ack_link"] += wrong_attempt
    errors["wrong_batch_link"] += wrong_batch
    errors["unattested_clock_link"] += clock
    errors["linear_timestamp_violation"] += linear
    return {
        "trace_contract_version": TRACE_CONTRACT_VERSION,
        "trace_row_count": len(rows),
        "unique_trace_id_count": len(by_trace),
        "logical_event_count": len(event_ids),
        "trace_linkage_error_count": errors["trace_linkage_error"],
        "wrong_attempt_ACK_link_count": errors["wrong_attempt_ack_link"],
        "wrong_batch_link_count": errors["wrong_batch_link"],
        "stale_timestamp_reuse_count": errors["stale_timestamp_reuse"],
        "unattested_clock_link_count": errors["unattested_clock_link"],
        "linear_timestamp_violation_count": errors[
            "linear_timestamp_violation"
        ],
        "schema_error_count": sum(
            count
            for name, count in errors.items()
            if name
            not in {
                "trace_linkage_error",
                "wrong_attempt_ack_link",
                "wrong_batch_link",
                "stale_timestamp_reuse",
                "unattested_clock_link",
                "linear_timestamp_violation",
            }
        ),
        "error_counts": dict(sorted((key, value) for key, value in errors.items() if value)),
        "clock_domain_attestation_passed": errors["unattested_clock_link"] == 0,
        "timing_trace_valid": sum(errors.values()) == 0,
    }


def successful_event_chains(
    rows: list[dict[str, Any]],
) -> list[dict[str, dict[str, Any]]]:
    by_trace = {row["trace_id"]: row for row in rows}
    chains: list[dict[str, dict[str, Any]]] = []
    for checkpoint in rows:
        if checkpoint["timestamp_name"] != "connector_checkpoint":
            continue
        chain: dict[str, dict[str, Any]] = {}
        current: dict[str, Any] | None = checkpoint
        visited: set[str] = set()
        while current is not None and current["trace_id"] not in visited:
            visited.add(current["trace_id"])
            chain[current["timestamp_name"]] = current
            parent = current["parent_trace_ref"]
            current = by_trace.get(parent) if parent else None
        if all(phase in chain for phase in PHASES):
            chains.append(chain)
    return chains


def latency_breakdown(
    rows: list[dict[str, Any]], event_modes: dict[str, str]
) -> dict[str, Any]:
    chains = successful_event_chains(rows)
    values_by_mode: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    segment_names = list(zip(PHASES, PHASES[1:]))
    for chain in chains:
        event_id = chain["capture_close"]["event_id"]
        mode = event_modes[event_id]
        for first, second in segment_names:
            values_by_mode[mode][f"{first}_to_{second}_ms"].append(
                (chain[second]["monotonic_ns"] - chain[first]["monotonic_ns"])
                / 1_000_000
            )
        values_by_mode[mode]["sensor_to_receiver_ms"].append(
            (
                chain["receiver_durable_commit"]["monotonic_ns"]
                - chain["event_creation"]["monotonic_ns"]
            )
            / 1_000_000
        )
        values_by_mode[mode]["connector_ingress_ack_ms"].append(
            (
                chain["ingress_ack"]["monotonic_ns"]
                - chain["connector_ingress_receive"]["monotonic_ns"]
            )
            / 1_000_000
        )
        values_by_mode[mode]["connector_to_receiver_ms"].append(
            (
                chain["receiver_durable_commit"]["monotonic_ns"]
                - chain["send_started"]["monotonic_ns"]
            )
            / 1_000_000
        )

    breakdowns: dict[str, Any] = {}
    for mode, metrics in values_by_mode.items():
        breakdowns[mode] = {
            "event_count": len(metrics["sensor_to_receiver_ms"]),
            "metrics": {
                name: {
                    "p50_ms": percentile(values, 0.50),
                    "p95_ms": percentile(values, 0.95),
                    "p99_ms": percentile(values, 0.99),
                    "max_ms": max(values, default=0.0),
                }
                for name, values in sorted(metrics.items())
            },
        }
    healthy_modes = {"healthy_nominal", "elevated", "burst"}
    healthy = [
        chain
        for chain in chains
        if event_modes[chain["capture_close"]["event_id"]] in healthy_modes
    ]

    def duration(first: str, second: str) -> list[float]:
        return [
            (chain[second]["monotonic_ns"] - chain[first]["monotonic_ns"])
            / 1_000_000
            for chain in healthy
        ]

    sensor = duration("event_creation", "receiver_durable_commit")
    ingress = duration("connector_ingress_receive", "ingress_ack")
    connector = duration("send_started", "receiver_durable_commit")
    return {
        "successful_event_chain_count": len(chains),
        "healthy_event_count": len(healthy),
        "fault_event_count": len(chains) - len(healthy),
        "fault_latency_excluded_from_healthy": True,
        "sensor_to_receiver_p50_ms": percentile(sensor, 0.50),
        "sensor_to_receiver_p95_ms": percentile(sensor, 0.95),
        "sensor_to_receiver_p99_ms": percentile(sensor, 0.99),
        "connector_ingress_ack_p95_ms": percentile(ingress, 0.95),
        "connector_to_receiver_p95_ms": percentile(connector, 0.95),
        "breakdowns": breakdowns,
    }
