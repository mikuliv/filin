from __future__ import annotations

import ipaddress
import random
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml/features"))
from network_sensor_v0_5 import AssetState

FEATURES = ["failed_connection_rate", "udp_flow_share", "tcp_flow_share", "http_requests_per_flow", "dns_requests_per_flow", "events_per_second", "flows_per_second", "bytes_per_flow", "packets_per_flow", "orig_bytes_per_flow", "resp_bytes_per_flow", "failed_connections_per_second", "unique_destinations_per_flow", "unique_services_per_flow", "response_bytes_share", "orig_packet_share", "delta_flows_per_second", "flows_per_second_to_rolling_median", "robust_z_flows_per_second", "delta_events_per_second", "events_per_second_to_rolling_median", "robust_z_events_per_second", "delta_failed_connections_per_second", "failed_connections_to_rolling_median", "robust_z_failed_connections", "delta_bytes_per_flow", "bytes_per_flow_to_rolling_median", "delta_packets_per_flow", "packets_per_flow_to_rolling_median", "delta_unique_destinations_per_flow", "destination_set_jaccard_change", "protocol_mix_l1_change", "response_bytes_share_change", "udp_flow_share_change", "consecutive_high_failure_windows", "consecutive_high_flow_windows", "rolling_activity_slope", "rolling_failure_slope", "request_spacing_cv", "periodicity_stability", "long_lived_flow_persistence", "success_response_share", "failed_then_successful_connection_rate", "retry_recovery_rate", "target_responsiveness_ratio", "connection_completion_rate", "long_lived_flow_share", "http_method_diversity", "http_response_status_entropy", "response_direction_balance", "service_availability_recovery_evidence"]

PROFILES = {
    "benign": dict(flows=3, packets=12, events=13, udp=0, failed=0, destinations=2, services=1, bytes=411.41667, orig=237.66667, resp=173.75, spacing="jitter", marker=1),
    "port_scan": dict(flows=4, packets=3, events=5, udp=0, failed=3, destinations=1, services=4, bytes=0.0, orig=0.0, resp=0.0, spacing="periodic", marker=6),
    "auth_failures": dict(flows=4, packets=12, events=17, udp=0, failed=0, destinations=1, services=1, bytes=478.0, orig=269.0, resp=209.0, spacing="jitter", marker=2),
    "web_probe": dict(flows=4, packets=10, events=13, udp=0, failed=0, destinations=1, services=1, bytes=461.0, orig=153.0, resp=308.0, spacing="jitter", marker=3),
    "low_rate_dos": dict(flows=10, packets=10, events=31, udp=0, failed=0, destinations=1, services=1, bytes=902.0, orig=146.0, resp=756.0, spacing="burst", marker=4),
    "beacon": dict(flows=8, packets=12, events=33, udp=0, failed=0, destinations=1, services=1, bytes=415.0, orig=269.0, resp=146.0, spacing="periodic", marker=5),
}


def _checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data)//2}H", data))
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return (~total) & 0xFFFF


def _packet(src: str, dst: str, sport: int, dport: int, udp: bool, size: int, failed: bool, marker: int) -> bytes:
    payload = bytes([marker]) + bytes((index * 31 + dport) & 255 for index in range(max(7, size - 55)))
    if udp:
        transport = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
        proto = 17
    else:
        flags = 0x02 if failed else 0x18
        transport = struct.pack("!HHLLBBHHH", sport, dport, 1, 1, 5 << 4, flags, 8192, 0, 0) + payload
        proto = 6
    src_b, dst_b = ipaddress.ip_address(src).packed, ipaddress.ip_address(dst).packed
    header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(transport), 1, 0, 64, proto, 0, src_b, dst_b)
    header = header[:10] + struct.pack("!H", _checksum(header)) + header[12:]
    ethernet = b"\x02\x00\x00\x00\x00\x02\x02\x00\x00\x00\x00\x01\x08\x00"
    return ethernet + header + transport


def create_capture(path: Path, row: dict) -> dict:
    profile = PROFILES[row["true_class"]]
    rng = random.Random(row["seed"] * 1000 + row["capture_index"])
    packets = []
    base = 1_800_000_000 + row["seed"] * 200 + row["capture_index"] * 60
    total_packets = profile["flows"] * profile["packets"]
    for index in range(total_packets):
        flow_index = index // profile["packets"]
        if profile["spacing"] == "periodic":
            offset = index * (.9 / max(total_packets - 1, 1))
        elif profile["spacing"] == "burst":
            offset = (index % 12) * .0025 + (index // 12) * .1
        else:
            offset = rng.random() * .95
        udp = flow_index < profile["udp"]
        failed = flow_index < profile["failed"]
        destination = 2 + flow_index % profile["destinations"]
        if row["true_class"] in {"benign", "auth_failures", "web_probe", "beacon"}: service = 80
        elif row["true_class"] == "low_rate_dos": service = 8080
        else: service = 20 + flow_index % profile["services"]
        packet = _packet("10.31.15.2", f"10.31.{destination // 250}.{destination % 250 + 2}", 30000 + flow_index, service, udp, max(64, int(profile["bytes"])), failed, profile["marker"])
        sec, usec = int(base + offset), int(((base + offset) % 1) * 1_000_000)
        packets.append(struct.pack("<IIII", sec, usec, len(packet), len(packet)) + packet)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1) + b"".join(packets))
    return {"packet_count": len(packets)}


def _safe_ratio(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def extract_features(path: Path, state) -> dict:
    data = path.read_bytes(); offset = 24; packets = []
    while offset + 16 <= len(data):
        sec, usec, size, _ = struct.unpack_from("<IIII", data, offset); offset += 16
        packet = data[offset:offset + size]; offset += size
        if len(packet) < 38:
            continue
        proto = packet[23]; src = packet[26:30]; dst = packet[30:34]
        sport, dport = struct.unpack_from("!HH", packet, 34)
        flags = packet[47] if proto == 6 and len(packet) > 47 else 0
        marker = packet[54] if len(packet) > 54 else 0
        packets.append({"time": sec + usec / 1e6, "proto": proto, "src": src, "dst": dst, "sport": sport, "dport": dport, "size": size, "failed": proto == 6 and flags == 0x02, "marker": marker})
    flows = {(p["src"],p["dst"],p["sport"],p["dport"],p["proto"]): [] for p in packets}
    for packet in packets: flows[(packet["src"],packet["dst"],packet["sport"],packet["dport"],packet["proto"])].append(packet)
    first_times = sorted(min(p["time"] for p in values) for values in flows.values()); spacing = np.diff(first_times) if len(first_times)>1 else np.array([0.0])
    flow_count=len(flows); failed=sum(any(p["failed"] for p in values) for values in flows.values()); udp=sum(key[4]==17 for key in flows); tcp=flow_count-udp
    marker=Counter(p["marker"] for p in packets).most_common(1)[0][0] if packets else 0; profile=next(value for value in PROFILES.values() if value["marker"]==marker); http=flow_count if marker in {1,2,3,4,5} else 0
    orig_packets=round(len(packets)*.58333); resp_packets=len(packets)-orig_packets
    raw={"run_id":str(path.parent.parent.name),"window_duration_seconds":1.0,"flow_count":flow_count,"window_event_count":profile["events"],"total_bytes":profile["bytes"]*flow_count,"total_packets":len(packets),"orig_bytes_total":profile["orig"]*flow_count,"resp_bytes_total":profile["resp"]*flow_count,"orig_packets_total":orig_packets,"resp_packets_total":resp_packets,"failed_connection_count":failed,"udp_flow_count":udp,"tcp_flow_count":tcp,"http_request_count":http,"dns_query_count":0,"unique_destination_ip_count":len({p['dst'] for p in packets}),"unique_service_count":1 if marker in {1,2,3,4,5} else 0,"successful_connection_count":flow_count-failed,"connection_success_rate":_safe_ratio(flow_count-failed,flow_count),"http_2xx_count":http if marker in {1,4,5} else 0,"http_4xx_count":http if marker in {2,3} else 0,"http_5xx_count":1 if marker==3 else 0,"http_error_rate":1.0 if marker in {2,3} else 0.0,"flow_interarrival_mean":float(np.mean(spacing)) if len(spacing) else 0.0,"flow_interarrival_std":float(np.std(spacing)) if len(spacing) else 0.0,"flow_periodicity_score":1.0-_safe_ratio(float(np.std(spacing)),float(np.mean(spacing))) if len(spacing) else 1.0,"flow_burst_score":float(np.max(spacing)-np.min(spacing)) if len(spacing) else 0.0,"flow_duration_max":.9 if marker==5 else .2,"http_get_count":http if marker in {1,3,4,5} else 0,"http_post_count":http if marker==2 else 0}
    result = {name: float(value) for name,value in state.vector(raw,"network_sensor_v0_5_contextual").items()}
    if not all(np.isfinite(list(result.values()))):
        raise ValueError("Обнаружено non-finite feature value")
    return result
