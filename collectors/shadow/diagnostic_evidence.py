"""Additive diagnostic evidence for future passive runtime trials.

The helpers in this module never participate in prediction, state transitions,
event identity or delivery decisions. Raw ACK bytes are accepted only from the
synthetic sink and remain in a caller-provided, gitignored runtime directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


LATENCY_STAGES = (
    "capture_closed_monotonic_ns", "zeek_completed_monotonic_ns",
    "feature_ready_monotonic_ns", "prediction_ready_monotonic_ns",
    "event_created_monotonic_ns", "spool_durable_monotonic_ns",
    "queue_registered_monotonic_ns", "send_started_monotonic_ns",
    "ack_received_monotonic_ns", "checkpoint_committed_monotonic_ns",
    "sink_committed_monotonic_ns",
)

ACK_STATUSES = {
    "accepted", "duplicate", "rejected_temporary", "rate_limited",
    "rejected_permanent", "malformed", "unknown", "authentication",
    "authorization",
}

_PRIVACY_PATTERNS = {
    "token": re.compile(r"(?i)(?:token|bearer)[\s=:]+[A-Za-z0-9._-]{6,}"),
    "password": re.compile(r"(?i)password[\s=:]+[^\s,;]+"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "url_query": re.compile(r"https?://[^\s?]+\?[^\s]+", re.I),
    "cookie": re.compile(r"(?i)(?:set-)?cookie[\s=:]+[^\s,;]+"),
    "hostname": re.compile(r"\b(?:[a-z0-9-]+\.)+(?:local|internal|example)\b", re.I),
    "local_user_path": re.compile(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/home/[^/\s]+)"),
}


def privacy_findings(payload: bytes | str) -> list[str]:
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    return sorted(name for name, pattern in _PRIVACY_PATTERNS.items() if pattern.search(text))


@dataclass
class LatencyTrace:
    trace_id: str
    event_id: str
    timestamps: dict[str, int] = field(default_factory=dict)

    def mark(self, stage: str, value: int | None = None) -> int:
        if stage not in LATENCY_STAGES:
            raise ValueError(f"unknown_latency_stage:{stage}")
        stamp = time.monotonic_ns() if value is None else int(value)
        previous = [self.timestamps[name] for name in LATENCY_STAGES if name in self.timestamps]
        if previous and stamp < previous[-1]:
            raise ValueError("non_monotonic_latency_trace")
        self.timestamps[stage] = stamp
        return stamp

    def validate(self, *, complete: bool = True) -> None:
        names = LATENCY_STAGES if complete else tuple(name for name in LATENCY_STAGES if name in self.timestamps)
        if complete and set(self.timestamps) != set(LATENCY_STAGES):
            raise ValueError("incomplete_latency_trace")
        values = [self.timestamps[name] for name in names]
        if values != sorted(values):
            raise ValueError("negative_latency")

    def analytical_record(self) -> dict[str, Any]:
        self.validate()
        values = [self.timestamps[name] for name in LATENCY_STAGES]
        return {
            "schema_version": "passive_latency_trace_v1",
            "trace_id": self.trace_id,
            "event_id": self.event_id,
            "clock": "monotonic_ns_single_process_domain",
            "timestamps": dict(self.timestamps),
            "capture_to_sink_ns": values[-1] - values[0],
            "non_negative": True,
        }


def normalized_cpu_sample(*, system_percent: float, process_tree_percent: float,
                          logical_cpu_count: int, sampling_interval_seconds: float,
                          warmup: bool = False) -> dict[str, Any]:
    if logical_cpu_count < 1 or sampling_interval_seconds <= 0:
        raise ValueError("invalid_cpu_measurement_parameters")
    normalized = process_tree_percent / logical_cpu_count
    return {
        "schema_version": "passive_cpu_sample_v1",
        "system_cpu_percent": float(system_percent),
        "process_tree_cpu_percent_raw": float(process_tree_percent),
        "process_tree_cpu_percent_per_host": float(normalized),
        "logical_cpu_count": logical_cpu_count,
        "sampling_interval_seconds": float(sampling_interval_seconds),
        "warmup_sample": bool(warmup),
        "meaning_of_100_percent": "all logical CPUs fully occupied for the interval",
    }


def capture_synthetic_ack(*, wire: bytes, status: str, event_id: str,
                          runtime_directory: str | Path, synthetic_sink: bool) -> dict[str, Any]:
    if not synthetic_sink:
        raise ValueError("raw_ack_requires_synthetic_sink")
    if status not in ACK_STATUSES:
        raise ValueError("unknown_ack_status")
    runtime = Path(runtime_directory)
    runtime.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(wire).hexdigest()
    raw_name = f"ack-{digest}.wire"
    raw_path = runtime / raw_name
    raw_path.write_bytes(wire)
    findings = privacy_findings(wire)
    return {
        "schema_version": "synthetic_ack_evidence_v1",
        "event_id": event_id,
        "status": status,
        "wire_sha256": digest,
        "wire_size": len(wire),
        "privacy_scan_passed": not findings,
        "privacy_finding_types": findings,
        "raw_runtime_name": raw_name,
        "synthetic_sink": True,
        "raw_ack_git_inclusion_permitted": False,
    }


def semantic_projection(runtime_result: dict[str, Any]) -> dict[str, Any]:
    """Remove additive diagnostic fields before semantic equivalence checks."""
    excluded = {"diagnostic_records", "latency_trace", "resource_samples", "ack_evidence"}
    return {key: value for key, value in runtime_result.items() if key not in excluded}


def instrumentation_equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return json.dumps(semantic_projection(left), sort_keys=True, separators=(",", ":")) == json.dumps(
        semantic_projection(right), sort_keys=True, separators=(",", ":")
    )
