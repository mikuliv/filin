"""Future-only feature profile with corrected duration/share semantics."""
from __future__ import annotations

import math
from typing import Any


PROFILE_NAME = "network_sensor_v0_6_integrity"
ORDERED_FEATURES = [
    "flow_count", "tcp_flow_count", "udp_flow_count", "failed_connection_count",
    "total_bytes", "total_packets", "http_request_count", "dns_query_count",
    "connection_failure_rate", "http_error_rate", "dns_error_rate",
    "orig_bytes_share", "orig_packets_share", "events_per_second",
    "flows_per_second", "bytes_per_second", "packets_per_second",
    "failed_connections_per_second", "unique_destinations_per_flow",
    "unique_services_per_flow",
]


def _required(row: dict[str, Any], name: str) -> float:
    if name not in row or row[name] in (None, ""):
        raise ValueError(f"required feature source is unavailable: {name}")
    try:
        value = float(row[name])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"feature source is not numeric: {name}") from exc
    if not math.isfinite(value):
        raise ValueError(f"feature source is not finite: {name}")
    return value


def _zero_safe(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def project_future_row(row: dict[str, Any]) -> dict[str, float]:
    """Project a row without silent missing-value or duration fallbacks."""
    duration = _required(row, "window_duration_seconds")
    if duration <= 0:
        raise ValueError("window_duration_seconds must be positive")
    flow = _required(row, "flow_count")
    total_bytes, total_packets = _required(row, "total_bytes"), _required(row, "total_packets")
    orig_bytes, resp_bytes = _required(row, "orig_bytes_total"), _required(row, "resp_bytes_total")
    orig_packets, resp_packets = _required(row, "orig_packets_total"), _required(row, "resp_packets_total")
    failed = _required(row, "failed_connection_count")
    result = {
        "flow_count": flow,
        "tcp_flow_count": _required(row, "tcp_flow_count"),
        "udp_flow_count": _required(row, "udp_flow_count"),
        "failed_connection_count": failed,
        "total_bytes": total_bytes,
        "total_packets": total_packets,
        "http_request_count": _required(row, "http_request_count"),
        "dns_query_count": _required(row, "dns_query_count"),
        "connection_failure_rate": _required(row, "connection_failure_rate"),
        "http_error_rate": _required(row, "http_error_rate"),
        "dns_error_rate": _required(row, "dns_error_rate"),
        "orig_bytes_share": _zero_safe(orig_bytes, orig_bytes + resp_bytes),
        "orig_packets_share": _zero_safe(orig_packets, orig_packets + resp_packets),
        "events_per_second": _required(row, "window_event_count") / duration,
        "flows_per_second": flow / duration,
        "bytes_per_second": total_bytes / duration,
        "packets_per_second": total_packets / duration,
        "failed_connections_per_second": failed / duration,
        "unique_destinations_per_flow": _zero_safe(_required(row, "unique_destination_ip_count"), flow),
        "unique_services_per_flow": _zero_safe(_required(row, "unique_service_count"), flow),
    }
    if list(result) != ORDERED_FEATURES or not all(math.isfinite(value) for value in result.values()):
        raise ValueError("future feature contract is invalid or non-finite")
    return result
