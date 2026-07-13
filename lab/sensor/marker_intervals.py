"""Strict marker-interval evidence for future research cycles.

Historical correlation functions are deliberately left unchanged.  New
builders must use this module and must never invent a numeric duration.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable


class MarkerIntervalError(ValueError):
    """Raised when an execution lacks one unambiguous positive interval."""


def parse_timestamp(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


@dataclass(frozen=True)
class MarkerInterval:
    execution_id: str
    marker_nonce: str
    start: float
    end: float
    duration_seconds: float
    source: str

    def evidence(self) -> dict[str, Any]:
        return asdict(self)


def _network_markers(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, list[float]]]:
    result: dict[str, dict[str, list[float]]] = {}
    for event in events:
        parts = str((event.get("raw") or {}).get("uri", "")).split("/")
        if len(parts) >= 4 and parts[1] == "sensor-marker" and parts[2] in {"start", "end"}:
            result.setdefault(parts[3], {}).setdefault(parts[2], []).append(parse_timestamp(event["timestamp"]))
    return result


def _control_markers(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, list[float]]]:
    result: dict[str, dict[str, list[float]]] = {}
    for record in records:
        nonce, kind = str(record.get("marker_nonce", "")), str(record.get("marker_type", ""))
        if nonce and kind in {"start", "end"}:
            result.setdefault(nonce, {}).setdefault(kind, []).append(parse_timestamp(record["timestamp"]))
    return result


def _one_pair(pairs: dict[str, dict[str, list[float]]], nonce: str, source: str) -> tuple[float, float] | None:
    pair = pairs.get(nonce, {})
    starts, ends = pair.get("start", []), pair.get("end", [])
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1:
        raise MarkerIntervalError(f"{source} marker pair for {nonce!r} is missing or ambiguous")
    if not starts[0] < ends[0]:
        raise MarkerIntervalError(f"{source} marker interval for {nonce!r} is not positive")
    return starts[0], ends[0]


def resolve_marker_intervals(
    manifest: dict[str, Any],
    events: Iterable[dict[str, Any]],
    marker_controls: Iterable[dict[str, Any]] = (),
    *,
    tolerance_seconds: float = 0.250,
) -> dict[str, MarkerInterval]:
    """Resolve one interval per execution, preferring captured sensor markers.

    Control-journal timestamps are secondary evidence.  When both sources are
    present they must agree within ``tolerance_seconds``.
    """
    network, control = _network_markers(events), _control_markers(marker_controls)
    resolved: dict[str, MarkerInterval] = {}
    for scenario in manifest.get("scenarios", []):
        execution_id = str(scenario.get("execution_id", ""))
        nonce = str(scenario.get("scenario_parameter_hash", ""))[:24]
        if not execution_id or not nonce:
            raise MarkerIntervalError("scenario lacks execution_id or marker nonce")
        primary = _one_pair(network, nonce, "sensor")
        secondary = _one_pair(control, nonce, "control")
        if primary and secondary and max(abs(primary[0] - secondary[0]), abs(primary[1] - secondary[1])) > tolerance_seconds:
            raise MarkerIntervalError(f"sensor/control marker disagreement for {execution_id}")
        pair, source = (primary, "sensor_marker") if primary else (secondary, "validated_control_marker")
        if pair is None:
            raise MarkerIntervalError(f"no marker interval for {execution_id}")
        start, end = pair
        resolved[execution_id] = MarkerInterval(execution_id, nonce, start, end, end - start, source)
    return resolved


def attach_interval_evidence(events: Iterable[dict[str, Any]], intervals: dict[str, MarkerInterval]) -> list[dict[str, Any]]:
    """Attach the exact interval used by future aggregation to assigned rows."""
    output = []
    for event in events:
        candidate = dict(event)
        execution_id = str(candidate.get("execution_id", ""))
        if candidate.get("correlation_status") == "assigned":
            if execution_id not in intervals:
                raise MarkerIntervalError(f"assigned event lacks interval evidence: {execution_id}")
            interval = intervals[execution_id]
            candidate.update({
                "correlation_interval_start": interval.start,
                "correlation_interval_end": interval.end,
                "correlation_interval_duration_seconds": interval.duration_seconds,
                "correlation_interval_source": interval.source,
            })
        output.append(candidate)
    return output
