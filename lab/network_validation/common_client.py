from __future__ import annotations

import argparse
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lab.network_validation.contracts import EXECUTION_SCHEMA, MARKER_SCHEMA, digest, load_json, validate_event, validate_scenario, write_canonical
from lab.network_validation.generators.base import NetworkAction
from lab.network_validation.generators.family_a import FamilyA
from lab.network_validation.generators.family_b import FamilyB

CLIENT_IDENTITY = "network-validation-common-client"
COMMON_HEADERS = {"User-Agent": "filin-network-validation/1", "Accept": "application/json", "X-Client-Role": "traffic-client"}
FAMILIES = {"family_a": FamilyA, "family_b": FamilyB}
TARGET_KEYS = {"web", "api", "control", "multi_port", "implementation", "network_identity"}


def validate_target_map(targets: dict[str, str]) -> None:
    required = TARGET_KEYS
    optional = {"client_image_digest", "target_image_digest"}
    if set(targets) - required - optional or required - set(targets):
        raise ValueError("target map fields mismatch")
    if any(not isinstance(value, str) or not value for value in targets.values()):
        raise ValueError("target map values must be non-empty strings")
    for capability in ("web", "api", "control"):
        parsed = urllib.parse.urlsplit(targets[capability])
        if parsed.scheme != "http" or not parsed.hostname:
            raise ValueError(f"invalid target URL for {capability}")
    if ":" not in targets["multi_port"]:
        raise ValueError("multi_port target must include a port")


def wall_time() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _request(url: str, action: NetworkAction, timeout: float) -> dict[str, Any]:
    payload = b"x" * action.payload_size if action.method in {"POST", "PUT"} else None
    request = urllib.request.Request(url.rstrip("/") + action.path, data=payload, method=action.method, headers=COMMON_HEADERS)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        error.read()
    return {"kind": "http", "status": status, "elapsed_ms": (time.monotonic() - started) * 1000, "payload_size": action.payload_size}


def _tcp(host: str, port: int, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            status = "connected"
    except OSError:
        status = "rejected_or_timeout"
    return {"kind": "tcp", "port": port, "status": status, "elapsed_ms": (time.monotonic() - started) * 1000}


def execute_action(action: NetworkAction, targets: dict[str, str], timeout: float) -> dict[str, Any]:
    if action.kind == "http":
        return _request(targets[action.capability], action, timeout)
    if action.kind == "tcp":
        host = targets[action.capability].split(":", 1)[0]
        return _tcp(host, int(action.port or 80), timeout)
    raise ValueError(f"unsupported network action: {action.kind}")


def _marker(kind: str, scenario: dict[str, Any], targets: dict[str, str], capture_id: str) -> dict[str, Any]:
    nonce = digest({"scenario_token": scenario["scenario_token"], "seed": scenario["seed"]})[:24]
    action = NetworkAction("http", "control", "GET", f"/sensor-marker/{kind}/{nonce}")
    execute_action(action, targets, 2.0)
    event = {
        "schema_version": MARKER_SCHEMA,
        "marker_nonce": nonce,
        "campaign_token": scenario["campaign_token"],
        "scenario_token": scenario["scenario_token"],
        "marker_type": kind,
        "monotonic_timestamp": time.monotonic(),
        "wall_clock_timestamp": wall_time(),
        "source": CLIENT_IDENTITY,
        "capture_association": capture_id,
    }
    validate_event(event, "marker")
    return event


def _background(scenario: dict[str, Any], targets: dict[str, str]) -> list[dict[str, Any]]:
    policy = scenario["background_traffic_policy"]
    events: list[dict[str, Any]] = []
    for _ in range(policy["http_requests"]):
        events.append(_request(targets["web"], NetworkAction("http", "web", path="/health"), 2.0))
    for _ in range(policy["dns_queries"]):
        try:
            socket.getaddrinfo("background.invalid", None)
            status = "resolved"
        except socket.gaierror:
            status = "queried"
        events.append({"kind": "dns", "status": status})
    for _ in range(policy["keepalive_count"]):
        events.append(_request(targets["control"], NetworkAction("http", "control", path="/keepalive"), 2.0))
    return events


def run_scenario(scenario: dict[str, Any], targets: dict[str, str], output_dir: Path, capture_id: str) -> dict[str, Any]:
    validate_scenario(scenario)
    validate_target_map(targets)
    family = FAMILIES[scenario["generator_family"]]()
    actions = family.actions(scenario)
    output_dir.mkdir(parents=True, exist_ok=True)
    markers = [_marker("start", scenario, targets, capture_id)]
    started_wall, started_mono = wall_time(), time.monotonic()
    results, retries = [], 0
    timeout = scenario["timeout_policy"]["read_ms"] / 1000
    for action in actions:
        try:
            results.append(execute_action(action, targets, timeout))
        except (OSError, TimeoutError, urllib.error.URLError) as error:
            attempt = 0
            while attempt < scenario["retry_policy"]["max_retries"]:
                attempt += 1
                retries += 1
                time.sleep(scenario["retry_policy"]["backoff_ms"] / 1000)
                try:
                    results.append(execute_action(action, targets, timeout))
                    break
                except (OSError, TimeoutError, urllib.error.URLError):
                    continue
            else:
                results.append({"kind": action.kind, "status": "failed", "error": type(error).__name__})
        if action.delay_ms:
            time.sleep(action.delay_ms / 1000)
    results.extend(_background(scenario, targets))
    remaining = scenario["requested_duration_seconds"] - (time.monotonic() - started_mono)
    if remaining > 0:
        time.sleep(remaining)
    markers.append(_marker("end", scenario, targets, capture_id))
    ended_mono, ended_wall = time.monotonic(), wall_time()
    execution = {
        "schema_version": EXECUTION_SCHEMA,
        "campaign_token": scenario["campaign_token"],
        "scenario_token": scenario["scenario_token"],
        "generator_family": scenario["generator_family"],
        "infrastructure_profile": scenario["infrastructure_profile"],
        "client_identity": CLIENT_IDENTITY,
        "target_identity": targets["implementation"],
        "start_timestamp": started_wall,
        "end_timestamp": ended_wall,
        "exit_code": 0,
        "execution_status": "technical_fixture_completed",
        "requested_parameter_digest": digest(scenario["parameter_vector"]),
        "client_image_digest": targets.get("client_image_digest", "unresolved"),
        "target_image_digest": targets.get("target_image_digest", "unresolved"),
        "network_identity": targets["network_identity"],
    }
    validate_event(execution, "execution")
    write_canonical(output_dir / "execution_event.json", execution)
    write_canonical(output_dir / "marker_events.json", markers)
    write_canonical(output_dir / "client_observations.json", {"technical_fixture": True, "duration_seconds": ended_mono - started_mono, "retry_count": retries, "actions": results})
    return execution


def main() -> int:
    parser = argparse.ArgumentParser(description="Common client runtime for disposable network validation fixtures.")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--target-map", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--capture-id", required=True)
    args = parser.parse_args()
    run_scenario(load_json(Path(args.scenario)), json.loads(args.target_map), Path(args.output_dir), args.capture_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
