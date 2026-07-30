from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

from .contracts import PARAMETER_SCHEMA, ContractError


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def observations_from_zeek(zeek_dir: Path) -> dict[str, Any]:
    conn, http, dns = _rows(zeek_dir / "conn.log"), _rows(zeek_dir / "http.log"), _rows(zeek_dir / "dns.log")
    scenario_http = [
        row for row in http
        if not str(row.get("uri", "")).startswith("/sensor-marker/")
        and str(row.get("uri", "")) not in {"/health", "/keepalive"}
    ]
    timestamps = sorted(float(row.get("ts", 0)) for row in scenario_http)
    spacing = [1000 * (right - left) for left, right in zip(timestamps, timestamps[1:])]
    starts = [float(row.get("ts", 0)) for row in conn]
    ends = [float(row.get("ts", 0)) + float(row.get("duration", 0) or 0) for row in conn]
    request_sizes = [int(row.get("request_body_len", 0) or 0) for row in scenario_http]
    repeated = {}
    for row in scenario_http:
        key = (row.get("method"), row.get("host"), row.get("uri"))
        repeated[key] = repeated.get(key, 0) + 1
    retries = sum(max(0, count - 1) for count in repeated.values())
    timeouts = sum(str(row.get("conn_state", "")) in {"S0", "SH", "SHR"} for row in conn)
    application_uids = {str(row.get("uid")) for row in http + dns if row.get("uid")}
    service_connections = [row for row in conn if row.get("uid") and str(row.get("uid")) not in application_uids]
    background = sum(str(row.get("uri", "")) in {"/health", "/keepalive"} for row in http)
    background += sum(str(row.get("query", "")).rstrip(".") == "background.invalid" for row in dns)
    http_evidence = "zeek:http.log" if http else "not_available"
    conn_evidence = "zeek:conn.log" if conn else "not_available"
    background_evidence = "zeek:http.log,dns.log" if (http or dns) else "not_available"
    return {
        "request_count": len(scenario_http) if http else None,
        "service_connection_count": len(service_connections) if service_connections else None,
        "episode_duration_seconds": max(ends) - min(starts) if starts and ends else None,
        "inter_request_spacing_ms": statistics.median(spacing) if spacing else None,
        "payload_size": statistics.median(request_sizes) if request_sizes else None,
        "retry_count": retries if scenario_http else None,
        "timeout_behavior": "timeout_observed" if timeouts else "response_observed" if conn else None,
        "response_order": "normal" if scenario_http and [float(row.get("ts", 0)) for row in scenario_http] == timestamps else None,
        "background_traffic_level": background if (http or dns) else None,
        "evidence_sources": {
            "request_count": http_evidence,
            "service_connection_count": conn_evidence,
            "episode_duration_seconds": conn_evidence,
            "inter_request_spacing_ms": http_evidence if spacing else "not_available",
            "payload_size": http_evidence,
            "retry_count": http_evidence,
            "timeout_behavior": conn_evidence,
            "response_order": "not_available",
            "background_traffic_level": background_evidence,
        },
    }


def verify_parameters(scenario: dict[str, Any], observed: dict[str, Any], tolerances: dict[str, float] | None = None) -> dict[str, Any]:
    tolerances = tolerances or {}
    requested = {
        "request_count": scenario["requested_request_count"],
        "episode_duration_seconds": scenario["requested_duration_seconds"],
        "inter_request_spacing_ms": scenario["requested_spacing_ms"],
        "payload_size": scenario["requested_payload_size"],
        "retry_count": scenario["retry_policy"]["max_retries"],
        "timeout_behavior": scenario["timeout_policy"]["expected"],
        "response_order": scenario["response_order_expectation"],
        "background_traffic_level": sum(scenario["background_traffic_policy"].values()),
    }
    unknown_tolerances = set(tolerances) - set(requested)
    if unknown_tolerances:
        raise ContractError(f"unknown parameter tolerances: {sorted(unknown_tolerances)}")
    for name, tolerance in tolerances.items():
        if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(float(tolerance)) or tolerance < 0:
            raise ContractError(f"invalid tolerance for {name}")
    checks = []
    for name, expected in requested.items():
        observed_name = "service_connection_count" if name == "request_count" and scenario["behavior_type"] == "service_discovery" else name
        actual = observed.get(observed_name)
        tolerance = tolerances.get(name, 0.0)
        evidence = observed.get("evidence_sources", {}).get(observed_name, observed.get("evidence_source", "not_available"))
        if actual is None:
            status = "not_observable"
        elif isinstance(actual, bool):
            status = "failed"
        elif name == "retry_count" and isinstance(actual, (int, float)):
            status = "passed" if 0 <= float(actual) <= float(expected) else "failed"
        elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            status = "passed" if math.isfinite(float(actual)) and abs(float(actual) - float(expected)) <= tolerance else "failed"
        elif name == "timeout_behavior" and expected == "either":
            status = "passed" if actual in {"response_observed", "timeout_observed"} else "failed"
        elif name == "timeout_behavior":
            status = "passed" if actual == f"{expected}_observed" else "failed"
        else:
            status = "passed" if actual == expected else "failed"
        checks.append({"parameter": name, "requested": expected, "observed": actual, "tolerance": tolerance, "status": status, "evidence_source": evidence})
    overall = "failed" if any(row["status"] == "failed" for row in checks) else "incomplete" if any(row["status"] == "not_observable" for row in checks) else "passed"
    return {"schema_version": PARAMETER_SCHEMA, "scenario_token": scenario["scenario_token"], "status": overall, "checks": checks}
