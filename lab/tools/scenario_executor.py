from __future__ import annotations

import json
import os
import random
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ALLOWED_TARGETS = {"target-web", "target-api", "control-api", "internal-dns", "target-ssh-sim"}
INTERNAL_DNS_NAMES = {"target-web", "target-api", "control-api", "target-ssh-sim", "filin-missing-service"}
REQUIRED_TRAFFIC_FIELDS = {"timestamp", "run_id", "run_sequence", "scenario_id", "target_host", "event_type", "execution_mode", "synthetic"}
CAMPAIGN_FIELDS = ("campaign_id", "campaign_version", "campaign_role", "campaign_run_index", "campaign_seed", "execution_id", "scenario_variant_id", "scenario_parameter_hash")


def capture_bpf(manifest: dict[str, Any]) -> list[str]:
    """Включить DNS только для явно изолированного будущего запуска."""
    if manifest.get("capture_dns") is True:
        allowed_roles = {"pre_training_smoke", "evidence_training", "evidence_internal_validation"}
        if manifest.get("campaign_role") not in allowed_roles:
            raise ValueError("DNS capture запрещён для этой роли кампании")
        policy = manifest.get("network_policy") or {}
        names = set(policy.get("allowed_dns_names") or [])
        if policy.get("scope") != "internal_docker_only" or policy.get("external_dns_allowed") is not False:
            raise ValueError("DNS capture требует internal-only network policy")
        if not names or not names <= INTERNAL_DNS_NAMES:
            raise ValueError("DNS capture содержит имя вне локального allowlist")
        return []
    # Preserve the historical capture behavior for immutable stages.
    return ["not", "port", "53"]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")


def execution_event(manifest: dict[str, Any], scenario: dict[str, Any], action: str, status: str, details: dict[str, Any]) -> dict[str, Any]:
    event = {
        "timestamp": utc_now(), "run_id": manifest.get("run_id"), "run_sequence": scenario.get("run_sequence"),
        "scenario_id": scenario.get("scenario_id"), "type": scenario.get("type"), "label": scenario.get("label"),
        "source_role": scenario.get("source_role"), "target_role": scenario.get("target_role"),
        "action": action, "status": status, "details": details,
    }
    for field in CAMPAIGN_FIELDS:
        if field in scenario:
            event[field] = scenario[field]
        elif field in manifest:
            event[field] = manifest[field]
    return event


def mock_event(manifest: dict[str, Any], scenario: dict[str, Any], index: int) -> dict[str, Any]:
    rng = random.Random(f"{scenario.get('scenario_id')}:{scenario.get('run_sequence')}:{index}")
    target = scenario.get("target_role", "target-web")
    return {
        "timestamp": utc_now(), "run_id": manifest.get("run_id"), "run_sequence": scenario.get("run_sequence"),
        "scenario_id": scenario.get("scenario_id"), "type": scenario.get("type"), "label": scenario.get("label"),
        "source_role": scenario.get("source_role"), "target_role": target, "event_source": "traffic_client",
        "observation_source": "generator", "execution_mode": "mock", "synthetic": True,
        "event_type": "http_request", "protocol": "http", "target_host": target, "target_port": 80,
        "method": "GET", "path": "/", "status": "ok", "status_code": 200,
        "bytes_in": rng.randint(100, 1200), "bytes_out": 0, "latency_ms": round(rng.uniform(5, 40), 2),
        "auth_success": None, "error": None, "details": {},
    }


def validate_client_event(event: dict[str, Any], manifest: dict[str, Any], scenario: dict[str, Any]) -> str | None:
    missing = REQUIRED_TRAFFIC_FIELDS - set(event)
    if missing:
        return f"Не хватает полей: {', '.join(sorted(missing))}"
    if event.get("target_host") not in ALLOWED_TARGETS:
        return "В событии указана цель вне allowlist"
    if event.get("run_id") != manifest.get("run_id") or event.get("scenario_id") != scenario.get("scenario_id"):
        return "Идентификаторы события не соответствуют текущему сценарию"
    if event.get("execution_mode") != "docker" or event.get("synthetic") is not False:
        return "Некорректная маркировка происхождения Docker-события"
    return None


def run_docker_scenario(manifest: dict[str, Any], scenario: dict[str, Any], compose_file: Path, compose_project_dir: Path, duration: int, max_events: int, max_rate: float, random_seed: int) -> tuple[list[dict[str, Any]], str, int]:
    command = [
        "docker", "compose", "-f", str(compose_file), "exec", "-T", "traffic-client", "python", "/app/client.py",
        "--scenario", str(scenario["scenario_id"]), "--run-id", str(manifest["run_id"]),
        "--run-sequence", str(scenario["run_sequence"]), "--duration-seconds", str(duration),
        "--max-events", str(max_events), "--max-rate", str(max_rate), "--random-seed", str(random_seed), "--output-format", "jsonl",
    ]
    execution_id = scenario.get("execution_id")
    if execution_id:
        command.extend([
            "--execution-id", str(execution_id),
            "--marker-nonce", str(scenario.get("scenario_parameter_hash", execution_id))[:24],
            "--marker-log", "/capture/marker_control.jsonl",
        ])
    capture_dir = os.environ.get("FILIN_SCENARIO_CAPTURE_DIR")
    if capture_dir:
        command.extend(["--marker-copies", "2"])
    elif manifest.get("campaign_id") == "filin-v0.3.7-hierarchical-training":
        command.extend(["--marker-copies", "5"])
    capture_started = False
    if capture_dir:
        capture_path = f"{capture_dir.rstrip('/')}/{int(scenario['run_sequence']):03d}.pcap"
        subprocess.run([
            "docker", "compose", "-f", str(compose_file), "exec", "-T", "-u", "root", "traffic-client",
            "sh", "-lc", f"mkdir -p {capture_dir} && rm -f {capture_path}",
        ], cwd=compose_project_dir, check=True)
        capture_command = [
            "docker", "compose", "-f", str(compose_file), "exec", "-d", "-u", "root", "traffic-client",
            "tcpdump", "-i", "eth0", "-B", "16384", "--immediate-mode", "-U", "-Z", "root",
            "-w", capture_path, *capture_bpf(manifest),
        ]
        subprocess.run(capture_command, cwd=compose_project_dir, check=True)
        capture_started = True
        time.sleep(0.5)
    try:
        completed = subprocess.run(command, cwd=compose_project_dir, capture_output=True, text=True, encoding="utf-8", timeout=max(30, duration + 30), check=False)
    finally:
        if capture_started:
            time.sleep(0.5)
            subprocess.run([
                "docker", "compose", "-f", str(compose_file), "exec", "-T", "-u", "root", "traffic-client",
                "pkill", "-INT", "tcpdump",
            ], cwd=compose_project_dir, check=False, capture_output=True)
            time.sleep(1.0)
    events: list[dict[str, Any]] = []
    invalid = 0
    for line in completed.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(event, dict) and validate_client_event(event, manifest, scenario) is None:
            events.append(event)
        else:
            invalid += 1
    notes = completed.stderr.strip()
    if invalid:
        notes = f"{notes}\nНепринятых строк JSONL: {invalid}".strip()
    return events, notes, completed.returncode


def execute_scenario(manifest: dict[str, Any], scenario: dict[str, Any], events_path: Path, traffic_path: Path, mock: bool, compose_file: Path | None = None, compose_project_dir: Path | None = None, time_scale: float = 1.0, random_seed: int = 42) -> dict[str, Any]:
    planned_duration = int(scenario.get("duration_seconds", 1))
    # traffic-client допускает не более минуты фактической активности на сценарий.
    effective_duration = min(60, max(1, round(planned_duration * time_scale)))
    mode = "mock" if mock else "docker"
    start_details = {"execution_mode": mode, "planned_duration_seconds": planned_duration, "effective_duration_seconds": effective_duration, "time_scale": time_scale}
    append_event(events_path, execution_event(manifest, scenario, "scenario_started", "ok", start_details))
    try:
        if mock:
            count = min(12, max(3, effective_duration))
            traffic_events = [mock_event(manifest, scenario, index) for index in range(count)]
            notes = ""
            return_code = 0
        else:
            if compose_file is None or compose_project_dir is None:
                raise ValueError("Для Docker-режима нужны путь к compose-файлу и рабочая папка compose.")
            # Для кампании обычные действия короткие; временная структура сохраняется
            # отдельно для low_rate_dos и beacon_simulation ниже.
            max_events = min(4, max(1, int(effective_duration * 3)))
            if manifest.get("campaign_id") in {
                "filin-v0.3.6-blind-holdout",
                "filin-v0.3.7-hierarchical-training",
                "filin-v0.3.7-hierarchical-validation",
            }:
                # Holdout execution markers are second-granular.  Keep prospective
                # windows wide enough that short requests cannot all land on the
                # same marker boundary and disappear from the correlated window.
                # Frozen run IDs, seeds, labels and composition remain unchanged.
                effective_duration = max(4, effective_duration)
                max_events = 8
            max_rate = 2.0 if scenario.get("label") in {"auth_failures", "low_rate_dos"} else 3.0
            variant = scenario.get("scenario_parameters") or {}
            if scenario.get("label") == "low_rate_dos":
                # Запас в одну секунду компенсирует дискретность UTC-журнала.
                effective_duration = max(7, int(variant.get("minimum_actual_duration_seconds", 6)))
                max_events = int(variant.get("request_count", 10))
                max_rate = min(5.0, float(variant.get("max_rate", 2.0)))
            elif scenario.get("label") == "beacon_simulation":
                effective_duration = max(8, int(variant.get("minimum_actual_duration_seconds", 8)))
                max_events = int(variant.get("heartbeat_count", 8))
                max_rate = min(5.0, 1000.0 / max(500.0, float(variant.get("base_interval_ms", 1000))))
            traffic_events, notes, return_code = run_docker_scenario(manifest, scenario, compose_file, compose_project_dir, effective_duration, max_events, max_rate, random_seed + int(scenario["run_sequence"]))
            if return_code:
                raise RuntimeError(f"traffic-client завершился с кодом {return_code}. {notes}".strip())
        for event in traffic_events:
            for field in CAMPAIGN_FIELDS:
                if field in scenario:
                    event[field] = scenario[field]
                elif field in manifest:
                    event[field] = manifest[field]
            append_event(traffic_path, event)
        # Manifest timestamps are second-granular.  Keep every interval open
        # after the client exits so adjacent marker windows cannot collapse;
        # low-rate traffic receives one additional second for Zeek flush.
        if not os.environ.get("FILIN_SCENARIO_CAPTURE_DIR"):
            time.sleep(1 + int(scenario.get("label") in {"low_rate_dos", "beacon_simulation"}))
        details = {**start_details, "traffic_events": len(traffic_events), "requests_sent": len(traffic_events), "errors": sum(1 for event in traffic_events if event.get("status") in {"error", "closed", "timeout"}), "stderr": notes}
        if manifest.get("campaign_role") == "pre_training_smoke":
            latencies = [float(event["latency_ms"]) for event in traffic_events if event.get("latency_ms") is not None]
            details["measured_mean_latency_ms"] = round(sum(latencies) / len(latencies), 3) if latencies else None
        append_event(events_path, execution_event(manifest, scenario, "scenario_finished", "completed", details))
        return {"status": "completed", "details": details}
    except Exception as error:
        details = {**start_details, "traffic_events": 0, "errors": 1, "message": str(error)}
        append_event(events_path, execution_event(manifest, scenario, "scenario_failed", "failed", details))
        return {"status": "failed", "details": details}
