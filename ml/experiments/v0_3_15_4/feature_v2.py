from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ml/features"))
from network_sensor_v0_5 import AssetState  # noqa: E402

CONTRACT = yaml.safe_load((Path(__file__).with_name("feature_contract_v2.yaml")).read_text(encoding="utf-8"))
FEATURES = CONTRACT["features"]


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _ratio(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def extract(zeek_dir: Path, state: AssetState, run_id: str) -> tuple[dict, dict]:
    conn = _rows(zeek_dir / "conn.log")
    http = _rows(zeek_dir / "http.log")
    dns = _rows(zeek_dir / "dns.log")
    if not conn:
        raise ValueError("zeek_conn_log_empty")
    flow_count = len(conn)
    failed_states = {"S0", "REJ", "RSTO", "RSTR", "SH", "SHR"}
    failed = sum(str(row.get("conn_state")) in failed_states for row in conn)
    udp = sum(row.get("proto") == "udp" for row in conn)
    orig_bytes = sum(float(row.get("orig_bytes", 0) or 0) for row in conn)
    resp_bytes = sum(float(row.get("resp_bytes", 0) or 0) for row in conn)
    orig_packets = sum(int(row.get("orig_pkts", 0) or 0) for row in conn)
    resp_packets = sum(int(row.get("resp_pkts", 0) or 0) for row in conn)
    times = sorted(float(row.get("ts", 0)) for row in conn)
    spacing = np.diff(times) if len(times) > 1 else np.array([0.0])
    statuses = [int(row.get("status_code", 0) or 0) for row in http]
    methods = [str(row.get("method", "")) for row in http if row.get("method")]
    duration = max([float(row.get("duration", 0) or 0) for row in conn] or [0.0])
    raw = {
        "run_id": run_id, "window_duration_seconds": 1.0,
        "flow_count": flow_count, "window_event_count": flow_count + len(http) + len(dns),
        "total_bytes": orig_bytes + resp_bytes, "total_packets": orig_packets + resp_packets,
        "orig_bytes_total": orig_bytes, "resp_bytes_total": resp_bytes,
        "orig_packets_total": orig_packets, "resp_packets_total": resp_packets,
        "failed_connection_count": failed, "udp_flow_count": udp, "tcp_flow_count": flow_count - udp,
        "http_request_count": len(http), "dns_query_count": len(dns),
        "unique_destination_ip_count": len({row.get("id.resp_h") for row in conn}),
        "unique_service_count": len({(row.get("proto"), row.get("id.resp_p")) for row in conn}),
        "successful_connection_count": flow_count - failed,
        "connection_success_rate": _ratio(flow_count - failed, flow_count),
        "http_2xx_count": sum(200 <= code < 300 for code in statuses),
        "http_4xx_count": sum(400 <= code < 500 for code in statuses),
        "http_5xx_count": sum(500 <= code < 600 for code in statuses),
        "http_error_rate": _ratio(sum(code >= 400 for code in statuses), len(statuses)),
        "flow_interarrival_mean": float(np.mean(spacing)), "flow_interarrival_std": float(np.std(spacing)),
        "flow_periodicity_score": max(0.0, 1.0 - _ratio(float(np.std(spacing)), float(np.mean(spacing)))),
        "flow_burst_score": float(np.max(spacing) - np.min(spacing)), "flow_duration_max": duration,
        "http_get_count": Counter(methods)["GET"], "http_post_count": Counter(methods)["POST"],
    }
    vector = {name: float(value) for name, value in state.vector(raw, "network_sensor_v0_5_contextual").items()}
    if list(vector) != FEATURES or not all(math.isfinite(value) for value in vector.values()):
        raise ValueError("invalid_feature_v2_vector")
    direct = {"failed_connection_rate", "udp_flow_share", "tcp_flow_share", "http_requests_per_flow", "dns_requests_per_flow", "events_per_second", "flows_per_second", "bytes_per_flow", "packets_per_flow", "orig_bytes_per_flow", "resp_bytes_per_flow", "failed_connections_per_second", "unique_destinations_per_flow", "unique_services_per_flow", "response_bytes_share", "orig_packet_share", "request_spacing_cv", "long_lived_flow_share", "http_method_diversity", "http_response_status_entropy"}
    provenance = {name: ("direct_observation" if name in direct else "deterministic_derivation") for name in FEATURES}
    sidecar = {"schema_version": "network_feature_provenance_v2", "feature_count": 51, "provenance": provenance, "contains_label": False, "contains_raw_payload": False, "model_input": False}
    return vector, sidecar
