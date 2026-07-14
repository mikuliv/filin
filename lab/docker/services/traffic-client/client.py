from __future__ import annotations

import argparse
import json
import random
import socket
import sys
import time
from datetime import UTC, datetime
from typing import Any

import requests

from future_workflows import WORKFLOW_PLANS, Action


ALLOWED_HTTP_TARGETS = {
    "target-web": "http://target-web",
    "target-api": "http://target-api:8080",
    "control-api": "http://control-api:8090",
}
ALLOWED_TARGETS = set(ALLOWED_HTTP_TARGETS) | {"internal-dns", "target-ssh-sim"}
SCAN_PORTS = [22, 80, 443, 8000, 8080, 5601]
WEB_PATHS = ["/", "/about.html", "/docs.html", "/files/sample-small.txt", "/files/sample-config.json"]
API_PATHS = ["/health", "/api/items", "/api/status", "/api/profile/test-user"]
PROBE_PATHS = ["/admin-test", "/debug-test", "/backup-test", "/old-login-test", "/not-found-test"]
DNS_NAMES = ["target-web", "target-api", "control-api", "target-ssh-sim", "filin-missing-service"]

SCENARIOS = {
    "benign_web_browsing": ("benign", "benign", "benign-client", "target-web"),
    "benign_api_workflow": ("benign", "benign", "benign-client", "target-api"),
    "benign_dns_discovery": ("benign", "benign", "benign-client", "internal-dns"),
    "benign_update_check": ("benign", "benign", "benign-client", "target-api"),
    "benign_file_download": ("benign", "benign", "benign-client", "target-web"),
    "benign_backup_sync": ("benign", "benign", "benign-client", "target-web"),
    "benign_log_shipping": ("benign", "benign", "benign-client", "target-api"),
    "benign_service_inventory": ("benign", "benign", "benign-client", "target-ssh-sim"),
    "benign_auth_retry_recovery": ("benign", "benign", "benign-client", "target-api"),
    "benign_broken_link_check": ("benign", "benign", "benign-client", "target-web"),
    "benign_parallel_transfer": ("benign", "benign", "benign-client", "target-web"),
    "benign_monitoring_heartbeat": ("benign", "benign", "benign-client", "control-api"),
    "benign_api_usage": ("benign", "benign", "benign-client", "target-api"),
    "benign_dns_activity": ("benign", "benign", "benign-client", "internal-dns"),
    "benign_file_downloads": ("benign", "benign", "benign-client", "target-web"),
    "benign_ssh_admin": ("benign", "benign", "benign-client", "target-ssh-sim"),
    "benign_database_pool_recovery": ("benign", "benign", "benign-client", "target-api"),
    "benign_multi_service_health": ("benign", "benign", "benign-client", "target-api"),
    "benign_long_poll_keepalive": ("benign", "benign", "benign-client", "control-api"),
    "benign_mirror_sync_burst": ("benign", "benign", "benign-client", "target-web"),
    "attack_port_scan": ("attack", "port_scan", "attacker-simulator", "target-web"),
    "attack_auth_failures": ("attack", "auth_failures", "attacker-simulator", "target-api"),
    "attack_web_probe": ("attack", "web_probe", "attacker-simulator", "target-web"),
    "attack_low_rate_dos": ("attack", "low_rate_dos", "attacker-simulator", "target-web"),
    "attack_beacon_simulation": ("attack", "beacon_simulation", "attacker-simulator", "control-api"),
}
for _holdout_id in (
    "benign_ci_cd_agent", "benign_service_mesh_readiness", "benign_dns_failover_rotation",
    "benign_object_storage_multipart", "benign_message_queue_consumer", "benign_certificate_renewal",
    "benign_remote_maintenance", "benign_batch_api_import", "benign_websocket_keepalive",
    "benign_package_mirror_refresh", "benign_backup_verification", "benign_log_rotation_shipping",
    "benign_multi_resolver_discovery", "benign_auth_token_refresh", "benign_polite_link_crawler",
    "benign_inventory_with_recovery",
):
    SCENARIOS[_holdout_id] = ("benign", "benign", "benign-client", "target-api")

for _v037_id in (
    "benign_incremental_backup_readback", "benign_chunked_replication_sync", "benign_repository_delta_sync",
    "benign_bounded_web_audit", "benign_metrics_scrape_wave", "benign_cache_prefetch",
    "benign_database_health_rotation", "benign_queue_consumer_rebalance", "benign_api_cursor_pagination",
    "benign_artifact_integrity_readback", "benign_certificate_inventory_refresh", "benign_service_discovery_reconcile",
    "benign_remote_patch_inventory", "benign_token_refresh_recovery", "benign_dns_cache_repopulation",
    "benign_log_ship_backoff", "benign_websocket_session_recovery", "benign_bulk_transaction_commit",
    "benign_snapshot_restore_check", "benign_multipart_replica_transfer", "benign_package_index_delta_pull",
    "benign_accessibility_link_review", "benign_observability_export_burst", "benign_cdn_cache_fill",
    "benign_database_failover_probe", "benign_consumer_group_rejoin", "benign_cursor_export_resume",
    "benign_release_bundle_validation", "benign_trust_store_refresh", "benign_registry_service_refresh",
    "benign_configuration_inventory", "benign_session_renewal_recovery", "benign_resolver_failover_cycle",
    "benign_audit_log_forward_retry", "benign_long_poll_reconnect", "benign_bulk_api_reconciliation",
):
    SCENARIOS[_v037_id] = ("benign", "benign", "benign-client", "target-api")


class SafetyError(ValueError):
    """Ошибка нарушения ограничений изолированного лабораторного стенда."""


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def event_base(args: argparse.Namespace, event_type: str, protocol: str, host: str, port: int | None) -> dict[str, Any]:
    scenario_type, label, source_role, target_role = SCENARIOS[args.scenario]
    return {
        "timestamp": now(),
        "run_id": args.run_id,
        "run_sequence": args.run_sequence,
        "scenario_id": args.scenario,
        "type": scenario_type,
        "label": label,
        "source_role": source_role,
        "target_role": target_role,
        "event_source": "traffic_client",
        "observation_source": "client",
        "execution_mode": "docker",
        "synthetic": False,
        "event_type": event_type,
        "protocol": protocol,
        "target_host": host,
        "target_port": port,
        "method": None,
        "path": None,
        "status": "ok",
        "status_code": None,
        "bytes_in": 0,
        "bytes_out": 0,
        "latency_ms": 0.0,
        "auth_success": None,
        "error": None,
        "details": {},
    }


def validate_args(args: argparse.Namespace) -> None:
    if args.scenario not in SCENARIOS:
        raise KeyError(args.scenario)
    if args.duration_seconds <= 0 or args.duration_seconds > 60:
        raise SafetyError("Длительность сценария должна быть от 1 до 60 секунд.")
    if args.max_events <= 0 or args.max_events > 100:
        raise SafetyError("max-events должен быть от 1 до 100.")
    if args.max_rate <= 0 or args.max_rate > 5:
        raise SafetyError("max-rate должен быть от 1 до 5 действий в секунду.")
    if args.output_format != "jsonl":
        raise SafetyError("Поддерживается только формат вывода jsonl.")


def emit(event: dict[str, Any]) -> None:
    # Время фиксируется непосредственно перед выдачей события, чтобы журнал
    # отражал фактическую временную структуру сценария.
    event["timestamp"] = now()
    print(json.dumps(event, ensure_ascii=False), flush=True)


def send_marker(marker_type: str, args: argparse.Namespace, headers: dict[str, str]) -> None:
    """Deliver a real marker before/after traffic; fail rather than silently losing it."""
    if not args.execution_id or not args.marker_nonce:
        return
    marker_log = getattr(args, "marker_log", None)

    def write_control_boundary() -> None:
        if not marker_log:
            return
        record = {
            "timestamp": time.time(),
            "run_id": args.run_id,
            "run_sequence": args.run_sequence,
            "execution_id": args.execution_id,
            "marker_nonce": args.marker_nonce,
            "marker_type": marker_type,
            "event_source": "traffic_client_marker_control",
        }
        with open(marker_log, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            file.flush()
    # The end boundary is recorded before end-marker packets are emitted.
    if marker_type == "end":
        write_control_boundary()
    # A capture can occasionally lose one otherwise successful HTTP marker.
    # Five independently acknowledged marker flows make long episode campaigns
    # robust; all carry the same nonce and are excluded from feature aggregation.
    for _copy in range(getattr(args, "marker_copies", 2)):
        last_error: Exception | None = None
        for _attempt in range(3):
            try:
                response = requests.post(
                    f"http://control-api:8090/sensor-marker/{marker_type}/{args.marker_nonce}",
                    headers={**headers, "X-Filin-Marker-Type": marker_type}, timeout=2.0,
                )
                response.raise_for_status()
                time.sleep(0.20)
                break
            except requests.RequestException as error:
                last_error = error
                time.sleep(0.15)
        else:
            raise RuntimeError(f"Не удалось отправить network marker {marker_type}: {last_error}")
    # The start boundary is recorded after start-marker packets are emitted.
    if marker_type == "start":
        write_control_boundary()


def request_event(args: argparse.Namespace, method: str, target: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if target not in ALLOWED_HTTP_TARGETS:
        raise SafetyError(f"HTTP-цель не входит в allowlist: {target}")
    if not path.startswith("/") or "://" in path or "?" in path:
        raise SafetyError("Разрешены только фиксированные внутренние пути без query-параметров.")
    url = ALLOWED_HTTP_TARGETS[target] + path
    event = event_base(args, "http_request", "http", target, 80 if target == "target-web" else (8080 if target == "target-api" else 8090))
    event["method"] = method
    event["path"] = path
    started = time.perf_counter()
    try:
        response = requests.request(method, url, json=payload, timeout=2.0, allow_redirects=False)
        event["status_code"] = response.status_code
        event["bytes_in"] = len(response.content)
        event["bytes_out"] = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) if payload else 0
        event["status"] = "ok" if response.status_code < 500 else "error"
        event["details"] = {"content_type": response.headers.get("content-type", "")}
    except requests.RequestException as error:
        event["status"] = "error"
        event["error"] = str(error)
    event["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return event


def tcp_event(args: argparse.Namespace, host: str, port: int, event_type: str) -> dict[str, Any]:
    if host not in ALLOWED_TARGETS:
        raise SafetyError(f"TCP-цель не входит в allowlist: {host}")
    event = event_base(args, event_type, "tcp", host, port)
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=1.0) as connection:
            if event_type == "admin_tcp_session_check":
                event["bytes_in"] = len(connection.recv(64))
        event["status"] = "open"
    except socket.timeout:
        event["status"] = "timeout"
    except OSError as error:
        event["status"] = "closed"
        event["error"] = str(error)
    event["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return event


def dns_event(args: argparse.Namespace, name: str) -> dict[str, Any]:
    if name not in DNS_NAMES:
        raise SafetyError(f"DNS-имя не входит в allowlist: {name}")
    event = event_base(args, "dns_resolution", "dns", name, 53)
    started = time.perf_counter()
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(name, None)})
        event["details"] = {"resolved_addresses": addresses, "scope": "internal"}
    except OSError as error:
        event["status"] = "error"
        event["error"] = str(error)
    event["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return event


def websocket_event(args: argparse.Namespace, operation: str) -> dict[str, Any]:
    """Perform a real local WebSocket upgrade; never represent it as GET traffic."""
    event = event_base(args, "websocket_session", "websocket", "control-api", 8090)
    event["method"], event["path"] = "WEBSOCKET", "/ws/lab"
    event["details"] = {"operation": operation}
    started = time.perf_counter()
    try:
        import base64, os
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        with socket.create_connection(("control-api", 8090), timeout=2.0) as connection:
            request = ("GET /ws/lab HTTP/1.1\r\nHost: control-api:8090\r\nUpgrade: websocket\r\n"
                       f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
            connection.sendall(request.encode("ascii")); response = connection.recv(512)
            event["bytes_out"], event["bytes_in"] = len(request), len(response)
            event["status"] = "open" if b" 101 " in response else "error"
            event["status_code"] = 101 if b" 101 " in response else None
    except OSError as error:
        event["status"], event["error"] = "error", str(error)
    event["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return event


def execute_workflow_plan(args: argparse.Namespace) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for action in WORKFLOW_PLANS[args.scenario]:
        if action.kind == "http":
            method, path = action.operation.split(":", 1)
            events.append(request_event(args, method, action.target, path, dict(action.payload) or None))
        elif action.kind == "dns": events.append(dns_event(args, action.target))
        elif action.kind == "tcp": events.append(tcp_event(args, action.target, int(action.operation), "admin_tcp_session_check"))
        elif action.kind == "websocket": events.append(websocket_event(args, action.operation))
        else: raise SafetyError(f"Unknown workflow action: {action.kind}")
    return events[: max(1, min(args.max_events, int(args.duration_seconds * args.max_rate)))]


def scenario_events(args: argparse.Namespace, rng: random.Random) -> list[dict[str, Any]]:
    capacity = max(1, min(args.max_events, int(args.duration_seconds * args.max_rate)))
    if args.scenario == "benign_web_browsing":
        return [request_event(args, "GET", "target-web", rng.choice(WEB_PATHS)) for _ in range(min(80, capacity))]
    if args.scenario == "benign_api_workflow":
        paths = ["/api/items", "/api/status", "/api/profile/test-user"]
        return [request_event(args, "GET", "target-api", rng.choice(paths)) for _ in range(min(40, capacity))]
    if args.scenario == "benign_dns_discovery":
        return [dns_event(args, rng.choice(DNS_NAMES)) for _ in range(min(30, capacity))]
    if args.scenario == "benign_update_check":
        return [request_event(args, "GET", "target-api", "/api/status") for _ in range(min(16, capacity))]
    if args.scenario == "benign_file_download":
        return [request_event(args, "GET", "target-web", rng.choice(["/files/sample-small.txt", "/files/sample-config.json"])) for _ in range(min(20, capacity))]
    if args.scenario == "benign_backup_sync":
        return [request_event(args, "GET", "target-web", "/files/sample-config.json") for _ in range(min(24, capacity))]
    if args.scenario == "benign_log_shipping":
        return [request_event(args, "POST", "target-api", "/api/items", {"source": "lab", "kind": "benign-log"}) for _ in range(min(24, capacity))]
    if args.scenario == "benign_service_inventory":
        return [tcp_event(args, "target-ssh-sim", 2222, "admin_tcp_session_check") for _ in range(min(12, capacity))]
    if args.scenario == "benign_auth_retry_recovery":
        events = [request_event(args, "POST", "target-api", "/api/login", {"username": "test-user", "password": "invalid-lab-password"})]
        events.extend(request_event(args, "GET", "target-api", "/api/profile/test-user") for _ in range(max(0, min(12, capacity) - 1)))
        return events
    if args.scenario == "benign_broken_link_check":
        return [request_event(args, "GET", "target-web", rng.choice(PROBE_PATHS)) for _ in range(min(12, capacity))]
    if args.scenario == "benign_parallel_transfer":
        paths = ["/files/sample-small.txt", "/files/sample-config.json"]
        return [request_event(args, "GET", "target-web", paths[index % len(paths)]) for index in range(min(32, capacity))]
    if args.scenario == "benign_monitoring_heartbeat":
        events = []
        for number in range(1, min(24, capacity) + 1):
            event = request_event(args, "POST", "control-api", "/beacon", {"agent": "benign-monitor", "status": "ok", "sequence": number})
            event["event_type"] = "heartbeat_request"
            events.append(event)
        return events
    if args.scenario == "benign_api_usage":
        return [request_event(args, "GET", "target-api", rng.choice(API_PATHS)) for _ in range(min(90, capacity))]
    if args.scenario == "benign_dns_activity":
        return [dns_event(args, rng.choice(DNS_NAMES)) for _ in range(min(60, capacity))]
    if args.scenario == "benign_file_downloads":
        paths = ["/files/sample-small.txt", "/files/sample-config.json"]
        return [request_event(args, "GET", "target-web", rng.choice(paths)) for _ in range(min(20, capacity))]
    if args.scenario == "benign_ssh_admin":
        return [tcp_event(args, "target-ssh-sim", 2222, "admin_tcp_session_check") for _ in range(min(15, capacity))]
    if args.scenario == "benign_database_pool_recovery":
        events = [request_event(args, "POST", "target-api", "/api/login", {"username": "test-user", "password": "invalid-lab-password"}) for _ in range(min(3, capacity))]
        events.extend(request_event(args, "GET", "target-api", "/api/status") for _ in range(min(5, max(0, capacity - len(events)))))
        return events
    if args.scenario == "benign_multi_service_health":
        events = [request_event(args, "GET", "target-api", "/health"), request_event(args, "GET", "target-web", "/")]
        events.extend(tcp_event(args, "target-ssh-sim", 2222, "admin_tcp_session_check") for _ in range(min(3, max(0, capacity - len(events)))))
        return events
    if args.scenario == "benign_long_poll_keepalive":
        return [request_event(args, "POST", "control-api", "/beacon", {"agent": "keepalive", "status": "ok", "sequence": index}) for index in range(1, min(8, capacity) + 1)]
    if args.scenario == "benign_mirror_sync_burst":
        paths = ["/files/sample-small.txt", "/files/sample-config.json"]
        return [request_event(args, "GET", "target-web", paths[index % 2]) for index in range(min(16, capacity))]
    if args.scenario == "attack_port_scan":
        return [tcp_event(args, "target-web", rng.choice(SCAN_PORTS), "tcp_connect_check") for _ in range(min(60, capacity))]
    if args.scenario == "attack_auth_failures":
        events = []
        for _ in range(min(30, capacity)):
            event = request_event(args, "POST", "target-api", "/api/login", {"username": "test-user", "password": "invalid-lab-password"})
            event["event_type"] = "auth_attempt"
            event["auth_success"] = False
            event["details"] = {"username_kind": "test_user", "credential_kind": "invalid_lab_value"}
            events.append(event)
        return events
    if args.scenario == "attack_web_probe":
        return [request_event(args, "GET", "target-web", rng.choice(PROBE_PATHS)) for _ in range(min(30, capacity))]
    if args.scenario == "attack_low_rate_dos":
        return [request_event(args, "GET", "target-web", rng.choice(["/", "/about.html"])) for _ in range(min(100, capacity))]
    if args.scenario == "attack_beacon_simulation":
        events = []
        for number in range(1, min(60, capacity) + 1):
            event = request_event(args, "POST", "control-api", "/beacon", {"agent": "filin-lab-client", "status": "alive", "sequence": number})
            event["event_type"] = "heartbeat_request"
            event["details"] = {"pattern": "учебный heartbeat", "sequence": number}
            events.append(event)
        return events
    if args.scenario in WORKFLOW_PLANS:
        return execute_workflow_plan(args)
    raise KeyError(args.scenario)


def main() -> None:
    parser = argparse.ArgumentParser(description="Безопасное выполнение одного лабораторного сценария внутри Docker-сети.")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-sequence", required=True, type=int)
    parser.add_argument("--duration-seconds", required=True, type=int)
    parser.add_argument("--max-events", required=True, type=int)
    parser.add_argument("--max-rate", required=True, type=float)
    parser.add_argument("--random-seed", required=True, type=int)
    parser.add_argument("--output-format", default="jsonl")
    parser.add_argument("--execution-id", default=None)
    parser.add_argument("--marker-nonce", default=None)
    parser.add_argument("--marker-log", default=None)
    parser.add_argument("--marker-copies", type=int, choices=range(1, 6), default=2)
    args = parser.parse_args()
    try:
        validate_args(args)
        rng = random.Random(args.random_seed)
        marker_headers = {
            "X-Filin-Run-Id": args.run_id,
            "X-Filin-Execution-Id": args.execution_id or "",
            "X-Filin-Marker-Nonce": args.marker_nonce or "",
        }
        send_marker("start", args, marker_headers)
        events = scenario_events(args, rng)
        delay = 1.0 / args.max_rate
        for index, event in enumerate(events):
            emit(event)
            if index + 1 < len(events):
                time.sleep(delay * rng.uniform(0.85, 1.15))
        send_marker("end", args, marker_headers)
    except KeyError:
        print("Неизвестный лабораторный сценарий.", file=sys.stderr)
        raise SystemExit(3)
    except SafetyError as error:
        print(f"Нарушение ограничений безопасности: {error}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as error:
        print(f"Ошибка выполнения сценария: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
