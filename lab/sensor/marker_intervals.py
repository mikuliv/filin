"""Copy-aware marker evidence for future research cycles.

Historical correlators remain unchanged.  A future interval starts at the last
captured start copy and ends at the first captured end copy, keeping marker
flows outside the model window.  Control journal records are independent
secondary evidence.  Reconciliation tolerance is dynamic: observed copy span
plus timestamp resolution and allowed capture jitter.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable


class MarkerIntervalError(ValueError):
    """An execution lacks one safe, unambiguous, positive interval."""


def parse_timestamp(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def _canonical_hash(domain: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(f"filin:{domain}:v1\n{encoded}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MarkerInterval:
    execution_id: str
    marker_nonce: str
    start: float
    end: float
    duration_seconds: float
    source: str
    sensor_start_count: int
    sensor_end_count: int
    control_start_count: int
    control_end_count: int
    sensor_start_first: float | None
    sensor_start_last: float | None
    sensor_end_first: float | None
    sensor_end_last: float | None
    control_start_first: float | None
    control_start_last: float | None
    control_end_first: float | None
    control_end_last: float | None
    sensor_start_spread_seconds: float
    sensor_end_spread_seconds: float
    control_start_spread_seconds: float
    control_end_spread_seconds: float
    reconciliation_tolerance_seconds: float
    sensor_control_reconciliation: str
    sensor_control_start_delta_seconds: float | None
    sensor_control_end_delta_seconds: float | None
    evidence_sha256: str

    def evidence(self) -> dict[str, Any]:
        return asdict(self)


def _marker_parts(event: dict[str, Any]) -> tuple[str, str] | None:
    parts = str((event.get("raw") or {}).get("uri", "")).split("/")
    if len(parts) >= 4 and parts[1] == "sensor-marker":
        return parts[2], parts[3]
    return None


def is_marker_event(event: dict[str, Any]) -> bool:
    return _marker_parts(event) is not None


def _network_markers(events: Iterable[dict[str, Any]], known_nonces: set[str]) -> dict[str, dict[str, list[float]]]:
    result: dict[str, dict[str, list[float]]] = {}
    for event in events:
        marker = _marker_parts(event)
        if marker is None:
            continue
        kind, nonce = marker
        if kind not in {"start", "end"}:
            raise MarkerIntervalError(f"unknown sensor marker type: {kind!r}")
        if nonce not in known_nonces:
            raise MarkerIntervalError("sensor marker nonce is not registered by the manifest")
        result.setdefault(nonce, {}).setdefault(kind, []).append(parse_timestamp(event["timestamp"]))
    return result


def _control_markers(records: Iterable[dict[str, Any]], known_nonces: set[str]) -> dict[str, dict[str, list[float]]]:
    result: dict[str, dict[str, list[float]]] = {}
    for record in records:
        nonce, kind = str(record.get("marker_nonce", "")), str(record.get("marker_type", ""))
        if kind not in {"start", "end"}:
            raise MarkerIntervalError(f"unknown control marker type: {kind!r}")
        if nonce not in known_nonces:
            raise MarkerIntervalError("control marker nonce is not registered by the manifest")
        result.setdefault(nonce, {}).setdefault(kind, []).append(parse_timestamp(record["timestamp"]))
    return result


def _values(groups: dict[str, dict[str, list[float]]], nonce: str, kind: str) -> list[float]:
    return sorted(groups.get(nonce, {}).get(kind, []))


def _bounds(values: list[float]) -> tuple[float | None, float | None, float]:
    if not values:
        return None, None, 0.0
    return values[0], values[-1], values[-1] - values[0]


def _complete(start: list[float], end: list[float]) -> bool:
    return bool(start and end)


def _manifest_nonce_map(manifest: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for scenario in manifest.get("scenarios", []):
        execution_id = str(scenario.get("execution_id", ""))
        nonce = str(scenario.get("marker_nonce") or str(scenario.get("scenario_parameter_hash", ""))[:24])
        if not execution_id or not nonce:
            raise MarkerIntervalError("scenario lacks execution_id or marker nonce")
        if nonce in mapping:
            raise MarkerIntervalError("marker nonce maps to more than one execution")
        mapping[nonce] = execution_id
    return mapping


def resolve_marker_intervals(
    manifest: dict[str, Any],
    events: Iterable[dict[str, Any]],
    marker_controls: Iterable[dict[str, Any]] = (),
    *,
    timestamp_resolution_seconds: float = 0.001,
    allowed_capture_jitter_seconds: float = 0.500,
) -> dict[str, MarkerInterval]:
    """Resolve deterministic boundaries while accepting repeated copies."""
    nonce_map = _manifest_nonce_map(manifest)
    network = _network_markers(events, set(nonce_map))
    control = _control_markers(marker_controls, set(nonce_map))
    resolved: dict[str, MarkerInterval] = {}
    for nonce, execution_id in nonce_map.items():
        ss, se = _values(network, nonce, "start"), _values(network, nonce, "end")
        cs, ce = _values(control, nonce, "start"), _values(control, nonce, "end")
        sensor_complete, control_complete = _complete(ss, se), _complete(cs, ce)
        if not sensor_complete and not control_complete:
            raise MarkerIntervalError(f"no complete marker interval for {execution_id}")

        # Last start / first end excludes all confirmed marker-copy flows.
        sensor_pair = (ss[-1], se[0]) if sensor_complete else None
        control_pair = (cs[-1], ce[0]) if control_complete else None
        chosen, source = (sensor_pair, "sensor_marker_copies") if sensor_pair else (control_pair, "validated_control_marker_copies")
        assert chosen is not None
        start, end = chosen
        if not start < end:
            raise MarkerIntervalError(f"marker interval for {execution_id} is not positive")

        ss_first, ss_last, ss_spread = _bounds(ss); se_first, se_last, se_spread = _bounds(se)
        cs_first, cs_last, cs_spread = _bounds(cs); ce_first, ce_last, ce_spread = _bounds(ce)
        tolerance = max(ss_spread, se_spread, cs_spread, ce_spread) + timestamp_resolution_seconds + allowed_capture_jitter_seconds
        start_delta = abs(sensor_pair[0] - control_pair[0]) if sensor_pair and control_pair else None
        end_delta = abs(sensor_pair[1] - control_pair[1]) if sensor_pair and control_pair else None
        if sensor_pair and control_pair:
            reconciliation = "agreed" if max(start_delta or 0.0, end_delta or 0.0) <= tolerance else "disagreed"
            if reconciliation == "disagreed":
                raise MarkerIntervalError(f"sensor/control marker disagreement for {execution_id}")
        else:
            reconciliation = "sensor_only" if sensor_pair else "control_only"

        if sensor_pair and not (ss_first <= sensor_pair[0] <= ss_last and se_first <= sensor_pair[1] <= se_last):
            raise MarkerIntervalError("selected sensor boundary is outside copy ranges")
        if control_pair and not (cs_first <= control_pair[0] <= cs_last and ce_first <= control_pair[1] <= ce_last):
            raise MarkerIntervalError("selected control boundary is outside copy ranges")

        values = {
            "execution_id": execution_id, "marker_nonce": nonce, "start": start, "end": end,
            "duration_seconds": end - start, "source": source,
            "sensor_start_count": len(ss), "sensor_end_count": len(se),
            "control_start_count": len(cs), "control_end_count": len(ce),
            "sensor_start_first": ss_first, "sensor_start_last": ss_last,
            "sensor_end_first": se_first, "sensor_end_last": se_last,
            "control_start_first": cs_first, "control_start_last": cs_last,
            "control_end_first": ce_first, "control_end_last": ce_last,
            "sensor_start_spread_seconds": ss_spread, "sensor_end_spread_seconds": se_spread,
            "control_start_spread_seconds": cs_spread, "control_end_spread_seconds": ce_spread,
            "reconciliation_tolerance_seconds": tolerance,
            "sensor_control_reconciliation": reconciliation,
            "sensor_control_start_delta_seconds": start_delta,
            "sensor_control_end_delta_seconds": end_delta,
        }
        values["evidence_sha256"] = _canonical_hash("marker_interval_evidence", values)
        resolved[execution_id] = MarkerInterval(**values)

    ordered = sorted(resolved.values(), key=lambda item: item.execution_id)
    for previous, current in zip(ordered, ordered[1:]):
        if max(previous.start, current.start) < min(previous.end, current.end):
            raise MarkerIntervalError("marker intervals overlap across executions")
    return resolved


def marker_interval_set_sha256(intervals: dict[str, MarkerInterval]) -> str:
    evidence = [intervals[key].evidence() for key in sorted(intervals)]
    return _canonical_hash("marker_interval_set", evidence)


def attach_interval_evidence(events: Iterable[dict[str, Any]], intervals: dict[str, MarkerInterval]) -> list[dict[str, Any]]:
    output = []
    for event in events:
        candidate = dict(event)
        execution_id = str(candidate.get("execution_id", ""))
        if is_marker_event(candidate) and candidate.get("correlation_status") == "assigned":
            raise MarkerIntervalError("marker control flow cannot be assigned for model aggregation")
        if candidate.get("correlation_status") == "assigned":
            if execution_id not in intervals:
                raise MarkerIntervalError(f"assigned event lacks interval evidence: {execution_id}")
            interval = intervals[execution_id]
            candidate.update({
                "correlation_interval_start": interval.start,
                "correlation_interval_end": interval.end,
                "correlation_interval_duration_seconds": interval.duration_seconds,
                "correlation_interval_source": interval.source,
                "marker_interval_evidence_sha256": interval.evidence_sha256,
            })
        output.append(candidate)
    return output
