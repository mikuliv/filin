"""Strict Zeek aggregation for the future ``network_sensor_v0_4`` profile.

Unlike the historical v0.3 builder, this module never pre-fills undeclared
measurements with zero.  Every returned feature is derived from an observed
Zeek field; empty inputs yield documented zeros for counts and ``NaN`` for
statistics that have no measured population.
"""
from __future__ import annotations

import math
from statistics import median, pstdev
from typing import Any

import numpy as np

from schema import NETWORK_SENSOR_V0_4


SUCCESS_STATES = {"SF", "S1", "S2", "S3"}
REJECTED_STATES = {"REJ", "RSTR"}
RESET_STATES = {"RSTO", "RSTR", "RSTOS0"}


def _number(value: Any) -> float | None:
    if value in (None, "", "-", "(empty)"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _quantile(values: list[float], q: float) -> float:
    return float(np.quantile(values, q)) if values else math.nan


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def aggregate_network_sensor_v4(events: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate correlated Zeek events without marker/control observations."""
    usable = [e for e in events if e.get("correlation_status") == "assigned"]
    conn = [e.get("raw", {}) for e in usable if e.get("sensor_log_type") == "conn"]
    http = [e.get("raw", {}) for e in usable if e.get("sensor_log_type") == "http"]
    dns = [e.get("raw", {}) for e in usable if e.get("sensor_log_type") == "dns"]
    durations = [n for raw in conn if (n := _number(raw.get("duration"))) is not None]
    orig_bytes = [n for raw in conn if (n := _number(raw.get("orig_bytes"))) is not None]
    resp_bytes = [n for raw in conn if (n := _number(raw.get("resp_bytes"))) is not None]
    orig_pkts = [n for raw in conn if (n := _number(raw.get("orig_pkts"))) is not None]
    resp_pkts = [n for raw in conn if (n := _number(raw.get("resp_pkts"))) is not None]
    states = [str(raw.get("conn_state")) for raw in conn if raw.get("conn_state") not in (None, "", "-")]
    timestamps = sorted(n for e in conn if (n := _number(e.get("ts"))) is not None)
    interarrival = [b - a for a, b in zip(timestamps, timestamps[1:])]
    flow_count = len(conn)
    orig_total, resp_total = sum(orig_bytes), sum(resp_bytes)
    orig_pkt_total, resp_pkt_total = sum(orig_pkts), sum(resp_pkts)
    http_statuses = [_number(raw.get("status_code")) for raw in http]
    dns_errors = [str(raw.get("rcode_name") or raw.get("rcode") or "").upper() for raw in dns]
    success_dns = sum(code in {"NOERROR", "0"} for code in dns_errors)
    error_dns = sum(code not in {"", "NOERROR", "0"} for code in dns_errors)
    result: dict[str, float] = {
        "flow_count": float(flow_count),
        "tcp_flow_count": float(sum(raw.get("proto") == "tcp" for raw in conn)),
        "udp_flow_count": float(sum(raw.get("proto") == "udp" for raw in conn)),
        "icmp_flow_count": float(sum(raw.get("proto") == "icmp" for raw in conn)),
        "unique_destination_ip_count": float(len({raw.get("id.resp_h") for raw in conn if raw.get("id.resp_h")})),
        "unique_destination_port_count": float(len({raw.get("id.resp_p") for raw in conn if raw.get("id.resp_p") not in (None, "")})),
        "unique_service_count": float(len({raw.get("service") for raw in conn if raw.get("service") not in (None, "", "-")})),
        "flow_duration_mean": float(sum(durations) / len(durations)) if durations else math.nan,
        "flow_duration_median": float(median(durations)) if durations else math.nan,
        "flow_duration_std": float(pstdev(durations)) if len(durations) > 1 else math.nan,
        "flow_duration_p95": _quantile(durations, .95), "flow_duration_max": max(durations, default=math.nan),
        "orig_bytes_total": orig_total, "resp_bytes_total": resp_total, "total_bytes": orig_total + resp_total,
        "orig_bytes_mean": _ratio(orig_total, len(orig_bytes)), "resp_bytes_mean": _ratio(resp_total, len(resp_bytes)),
        "orig_resp_bytes_ratio": _ratio(orig_total, orig_total + resp_total),
        "orig_packets_total": orig_pkt_total, "resp_packets_total": resp_pkt_total, "total_packets": orig_pkt_total + resp_pkt_total,
        "orig_packets_mean": _ratio(orig_pkt_total, len(orig_pkts)), "resp_packets_mean": _ratio(resp_pkt_total, len(resp_pkts)),
        "orig_resp_packets_ratio": _ratio(orig_pkt_total, orig_pkt_total + resp_pkt_total),
        "successful_connection_count": float(sum(state in SUCCESS_STATES for state in states)),
        "failed_connection_count": float(sum(state not in SUCCESS_STATES for state in states)),
        "rejected_connection_count": float(sum(state in REJECTED_STATES for state in states)),
        "reset_connection_count": float(sum(state in RESET_STATES for state in states)),
        "connection_success_rate": _ratio(sum(state in SUCCESS_STATES for state in states), flow_count),
        "connection_failure_rate": _ratio(sum(state not in SUCCESS_STATES for state in states), flow_count),
        "unique_conn_state_count": float(len(set(states))),
        "http_request_count": float(len(http)), "http_get_count": float(sum(raw.get("method") == "GET" for raw in http)),
        "http_post_count": float(sum(raw.get("method") == "POST" for raw in http)),
        "http_2xx_count": float(sum(200 <= status < 300 for status in http_statuses if status is not None)),
        "http_4xx_count": float(sum(400 <= status < 500 for status in http_statuses if status is not None)),
        "http_5xx_count": float(sum(500 <= status < 600 for status in http_statuses if status is not None)),
        "http_error_rate": _ratio(sum(status >= 400 for status in http_statuses if status is not None), len(http)),
        "unique_http_host_count": float(len({raw.get("host") for raw in http if raw.get("host")})),
        "unique_uri_count": float(len({raw.get("uri") for raw in http if raw.get("uri")})),
        "http_request_body_bytes": sum(_number(raw.get("request_body_len")) or 0.0 for raw in http),
        "http_response_body_bytes": sum(_number(raw.get("response_body_len")) or 0.0 for raw in http),
        "dns_query_count": float(len(dns)), "dns_success_count": float(success_dns), "dns_error_count": float(error_dns),
        "unique_dns_query_count": float(len({raw.get("query") for raw in dns if raw.get("query")})),
        "unique_dns_answer_count": float(len({answer for raw in dns for answer in (raw.get("answers") or []) if answer})),
        "dns_error_rate": _ratio(error_dns, len(dns)),
        "flow_interarrival_mean": float(sum(interarrival) / len(interarrival)) if interarrival else math.nan,
        "flow_interarrival_std": float(pstdev(interarrival)) if len(interarrival) > 1 else math.nan,
        "flow_periodicity_score": _ratio(1.0, 1.0 + pstdev(interarrival)) if len(interarrival) > 1 else math.nan,
        "flow_burst_score": _ratio(sum(1 for value in interarrival if value <= (sum(interarrival) / len(interarrival))), len(interarrival)) if interarrival else math.nan,
    }
    if list(result) != NETWORK_SENSOR_V0_4:
        raise RuntimeError("network_sensor_v0_4 aggregation does not match its declared schema")
    return result
