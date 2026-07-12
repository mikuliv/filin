"""Детерминированные профили признаков эксперимента Филин v0.3.4.

Этот модуль не читает наборы v0.3.3 и не содержит метаданных в матрице X.
Все производные величины определены только через поля ``network_sensor_v0_3``.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from schema import NETWORK_SENSOR_V0_3

CONTROL_PROFILE = "network_sensor_v0_3_control"
RATE_PROFILE = "network_sensor_v0_4_rates"
HYBRID_PROFILE = "network_sensor_v0_4_hybrid"

RATE_FEATURES = [
    "failed_connection_rate", "udp_flow_share", "tcp_flow_share",
    "http_requests_per_flow", "dns_requests_per_flow", "events_per_second",
    "flows_per_second", "bytes_per_flow", "packets_per_flow",
    "orig_bytes_per_flow", "resp_bytes_per_flow",
    "failed_connections_per_second", "unique_destinations_per_flow",
    "unique_services_per_flow", "response_bytes_share", "orig_packet_share",
]
VOLUME_SENSITIVE = [
    "failed_connection_count", "udp_flow_count", "resp_bytes_mean",
    "http_request_count", "window_event_count", "orig_bytes_mean",
    "connection_failure_rate", "orig_resp_packets_ratio",
]
HYBRID_BASE = [
    "flow_duration_mean", "flow_duration_median", "flow_duration_std",
    "flow_duration_p95", "flow_duration_max", "connection_success_rate",
    "connection_failure_rate", "http_error_rate", "dns_error_rate",
    "flow_interarrival_mean", "flow_interarrival_std", "flow_periodicity_score",
    "flow_burst_score", "unique_conn_state_count",
]
HYBRID_RAW = ["flow_count", "total_bytes", "total_packets", "http_request_count", "failed_connection_count"]
HYBRID_LOG = [f"log1p_{name}" for name in HYBRID_RAW]
HYBRID_FEATURES = [*HYBRID_BASE, *RATE_FEATURES, *HYBRID_RAW, *HYBRID_LOG]
MAX_HYBRID_FEATURES = 90


def profile_features(profile: str) -> list[str]:
    if profile == CONTROL_PROFILE:
        return list(NETWORK_SENSOR_V0_3)
    if profile == RATE_PROFILE:
        return list(RATE_FEATURES)
    if profile == HYBRID_PROFILE:
        return list(HYBRID_FEATURES)
    raise ValueError(f"Неизвестный профиль v0.3.4: {profile}")


def _value(row: dict[str, Any], name: str) -> float:
    value = row.get(name, 0.0)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _divide(numerator: float, denominator: float, minimum: float = 1.0) -> float:
    return numerator / max(denominator, minimum)


def derive_rates(row: dict[str, Any]) -> dict[str, float]:
    """Возвращает только конечные rates/shares с явной защитой нулей."""
    flow = _value(row, "flow_count")
    duration = _value(row, "window_duration_seconds")
    total_bytes = _value(row, "total_bytes")
    total_packets = _value(row, "total_packets")
    orig_bytes = _value(row, "orig_bytes_total")
    resp_bytes = _value(row, "resp_bytes_total")
    orig_packets = _value(row, "orig_packets_total")
    resp_packets = _value(row, "resp_packets_total")
    values = {
        "failed_connection_rate": _divide(_value(row, "failed_connection_count"), flow),
        "udp_flow_share": _divide(_value(row, "udp_flow_count"), flow),
        "tcp_flow_share": _divide(_value(row, "tcp_flow_count"), flow),
        "http_requests_per_flow": _divide(_value(row, "http_request_count"), flow),
        "dns_requests_per_flow": _divide(_value(row, "dns_query_count"), flow),
        "events_per_second": _divide(_value(row, "window_event_count"), duration, 1e-9),
        "flows_per_second": _divide(flow, duration, 1e-9),
        "bytes_per_flow": _divide(total_bytes, flow),
        "packets_per_flow": _divide(total_packets, flow),
        "orig_bytes_per_flow": _divide(orig_bytes, flow),
        "resp_bytes_per_flow": _divide(resp_bytes, flow),
        "failed_connections_per_second": _divide(_value(row, "failed_connection_count"), duration, 1e-9),
        "unique_destinations_per_flow": _divide(_value(row, "unique_destination_ip_count"), flow),
        "unique_services_per_flow": _divide(_value(row, "unique_service_count"), flow),
        "response_bytes_share": _divide(resp_bytes, orig_bytes + resp_bytes),
        "orig_packet_share": _divide(orig_packets, orig_packets + resp_packets),
    }
    return {name: float(value) if math.isfinite(value) else 0.0 for name, value in values.items()}


def project_row(row: dict[str, Any], profile: str) -> dict[str, float]:
    rates = derive_rates(row)
    if profile == CONTROL_PROFILE:
        return {name: _value(row, name) for name in NETWORK_SENSOR_V0_3}
    if profile == RATE_PROFILE:
        return rates
    if profile == HYBRID_PROFILE:
        result = {name: _value(row, name) for name in HYBRID_BASE}
        result.update(rates)
        result.update({name: _value(row, name) for name in HYBRID_RAW})
        result.update({f"log1p_{name}": math.log1p(max(_value(row, name), 0.0)) for name in HYBRID_RAW})
        if len(result) > MAX_HYBRID_FEATURES:
            raise ValueError("Превышен лимит hybrid-признаков")
        return result
    raise ValueError(f"Неизвестный профиль v0.3.4: {profile}")


def project_rows(rows: Iterable[dict[str, Any]], profile: str) -> list[dict[str, float]]:
    return [project_row(row, profile) for row in rows]
