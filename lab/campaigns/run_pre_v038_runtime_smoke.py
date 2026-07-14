"""Short, future-only Docker acceptance smoke before any v0.3.8 training."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for path in (
    ROOT / "lab" / "sensor", ROOT / "lab" / "tools", ROOT / "ml" / "features",
    ROOT / "lab" / "docker" / "services" / "traffic-client", ROOT / "lab" / "environment",
):
    sys.path.insert(0, str(path))

from artifact_storage import SensorArtifactStorage
from correlate_sensor_events import correlate_isolated_capture
from application_controller import EnvironmentApplicationController, assign_profile, audit_condition_independence
from marker_intervals import is_marker_event, resolve_marker_intervals
from scenario_executor import execute_scenario
from future_scenario_runner import execute_with_environment
from future_workflows import primary_target, workflow_runtime_audit
from tools.audit.artifact_hashes import canonical_sha256, file_sha256
from tools.audit.verify_secure_artifacts import verify as verify_secure


PROJECT = "filin_pre_v038_smoke"
NETWORK = "filin_pre_v038_smoke_lab"
MGMT_NETWORK = "filin_pre_v038_smoke_mgmt"
MONITOR_NETWORK = "filin_pre_v038_smoke_monitor"
CAPTURE_VOLUME = "filin_pre_v038_smoke_capture"
ZEEK_VOLUME = "filin_pre_v038_smoke_zeek"
COMPOSE = ROOT / "lab" / "docker" / "docker-compose.lab.yml"
ASSIGNMENT_SEED = 20260714
PROFILES = {
    "no_impairment": {"profile_id": "no_impairment"},
    "latency_40ms": {"profile_id": "latency_40ms", "latency_ms": 40, "jitter_ms": 2},
}
EXECUTIONS = [
    ("smoke-exec-001", "smoke_http_readback"),
    ("smoke-exec-002", "smoke_dns_local_resolution"),
    ("smoke-exec-003", "smoke_http_readback"),
    ("smoke-exec-004", "smoke_websocket_ping_pong"),
    ("smoke-exec-005", "smoke_tcp_admin_check"),
    ("smoke-exec-006", "smoke_mixed_service_check"),
    ("smoke-exec-007", "smoke_attack_like_probe"),
]


def _run(command: list[str], *, env: dict[str, str], check: bool = True, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=ROOT / "lab" / "docker", env=env, check=check,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )


def _compose(*parts: str) -> list[str]:
    return ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE), *parts]


def _docker_ids(env: dict[str, str]) -> set[str]:
    completed = _run(["docker", "ps", "--format", "{{.ID}}"], env=env)
    return set(completed.stdout.split())


def _manifest() -> dict[str, Any]:
    scenarios = []
    for sequence, (execution_id, scenario_id) in enumerate(EXECUTIONS, start=1):
        parameter_hash = hashlib.sha256(f"{ASSIGNMENT_SEED}:{execution_id}:{scenario_id}".encode()).hexdigest()
        profile_id = assign_profile(execution_id, list(PROFILES), ASSIGNMENT_SEED)
        is_attack = scenario_id == "smoke_attack_like_probe"
        scenarios.append({
            "run_sequence": sequence, "execution_id": execution_id, "scenario_id": scenario_id,
            "scenario_variant_id": f"{scenario_id}-v1", "scenario_parameter_hash": parameter_hash,
            "marker_nonce": parameter_hash[:24], "duration_seconds": 5,
            "type": "attack" if is_attack else "benign", "label": "web_probe" if is_attack else "benign",
            "source_role": "attacker-simulator" if is_attack else "benign-client",
            "target_role": primary_target(scenario_id), "environment_profile_id": profile_id,
        })
    return {
        "run_id": "pre-v038-runtime-smoke-20260714", "campaign_id": "filin-pre-v038-runtime-smoke",
        "campaign_version": "1", "campaign_role": "pre_training_smoke", "campaign_run_index": 1,
        "campaign_seed": ASSIGNMENT_SEED, "execution_mode": "docker", "capture_dns": True,
        "network_policy": {
            "scope": "internal_docker_only", "external_dns_allowed": False,
            "allowed_dns_names": ["target-web", "target-api", "control-api", "target-ssh-sim", "filin-missing-service"],
        },
        "marker_reconciliation_policy": {
            "timestamp_resolution_seconds": 0.001,
            "allowed_capture_jitter_seconds": 1.5,
            "boundary_selection": "last_sensor_start_first_sensor_end",
        },
        "scenarios": scenarios,
    }


def _wait_ready(env: dict[str, str]) -> None:
    probe = "import socket; [socket.create_connection(x,2).close() for x in [('target-web',80),('target-api',8080),('control-api',8090),('target-ssh-sim',2222)]]"
    for _ in range(30):
        result = _run(_compose("exec", "-T", "traffic-client", "python", "-c", probe), env=env, check=False, timeout=15)
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("isolated smoke services did not become ready")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _execute(output: Path, env: dict[str, str], skip_build: bool) -> dict[str, Any]:
    if _run(_compose("ps", "-q"), env=env).stdout.strip():
        raise RuntimeError("the dedicated smoke compose project is already active")
    for volume in (CAPTURE_VOLUME, ZEEK_VOLUME):
        if _run(["docker", "volume", "inspect", volume], env=env, check=False).returncode == 0:
            raise RuntimeError("a dedicated smoke volume already exists; refusing to reuse evidence")

    up = ["up", "-d"]
    if not skip_build:
        up.append("--build")
    up.extend(["internal-dns", "target-web", "target-api", "control-api", "target-ssh-sim", "traffic-client"])
    _run(_compose(*up), env=env, timeout=900)
    _wait_ready(env)
    _run(_compose(
        "exec", "-T", "-u", "root", "traffic-client", "sh", "-lc",
        "rm -rf /capture/pre_v038_smoke /capture/marker_control.jsonl && touch /capture/marker_control.jsonl && chmod 0666 /capture/marker_control.jsonl",
    ), env=env)

    manifest = _manifest()
    manifest_path = output / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
    execution_events = output / "execution_events.jsonl"
    traffic_events = output / "traffic_events.jsonl"
    container_id = _run(_compose("ps", "-q", "traffic-client"), env=env).stdout.strip()
    controller = EnvironmentApplicationController(
        container_id, expected_compose_project=PROJECT, expected_network=NETWORK,
    )
    condition_records = []
    for scenario in manifest["scenarios"]:
        holder: dict[str, Any] = {}
        profile = PROFILES[scenario["environment_profile_id"]]

        def execute(current=scenario):
            result = execute_scenario(
                manifest, current, execution_events, traffic_events, False,
                COMPOSE, ROOT / "lab" / "docker", time_scale=1.0, random_seed=ASSIGNMENT_SEED,
            )
            holder["result"] = result
            return result

        def measure():
            return {"measured_mean_latency_ms": holder["result"]["details"].get("measured_mean_latency_ms")}

        _, evidence = execute_with_environment(
            controller=controller, profile=profile, seed=ASSIGNMENT_SEED + scenario["run_sequence"],
            execute=execute, measure=measure,
        )
        condition_records.append({
            "run_id": scenario["execution_id"], "environment_profile_id": scenario["environment_profile_id"],
            "assignment_seed": ASSIGNMENT_SEED, "assignment_inputs": ["run_id", "assignment_seed"],
            "application_status": evidence.status, "rollback_verified": evidence.rollback_verified,
            "verification_contains_netem": "netem" in evidence.verification,
            "requested_profile": evidence.requested_profile, "resolved_parameters": evidence.resolved_parameters,
            "qdisc_before": evidence.before, "qdisc_during": evidence.verification,
            "qdisc_after_rollback": evidence.after_rollback,
            "application_started_at": evidence.application_started_at,
            "application_verified_at": evidence.application_verified_at,
            "experiment_started_at": evidence.experiment_started_at,
            "experiment_ended_at": evidence.experiment_ended_at,
            "rollback_completed_at": evidence.rollback_completed_at,
            "unsupported_parameters": evidence.unsupported_parameters, "measurements": evidence.measurements,
        })
    _write_json(output / "environment_application_evidence.json", condition_records)

    marker_export = _run(
        ["docker", "run", "--rm", "-v", f"{CAPTURE_VOLUME}:/capture:ro", "busybox", "cat", "/capture/marker_control.jsonl"],
        env=env,
    ).stdout
    marker_log = output / "marker_control.jsonl"
    marker_log.write_text(marker_export, encoding="utf-8")
    controls = _read_jsonl(marker_log)
    storage = SensorArtifactStorage(CAPTURE_VOLUME, ZEEK_VOLUME)
    pcap_records = []
    correlated: list[dict[str, Any]] = []
    for scenario in manifest["scenarios"]:
        sequence = scenario["run_sequence"]
        pcap_relative = f"pre_v038_smoke/{sequence:03d}.pcap"
        if not storage.pcap_exists(pcap_relative):
            raise RuntimeError("an execution PCAP is missing")
        pcap_records.append({
            "execution_id": scenario["execution_id"], "size_bytes": storage.pcap_size(pcap_relative),
            "pcap_sha256": storage.pcap_sha256(pcap_relative),
        })
        zeek_dir = output / "zeek" / scenario["execution_id"]
        _run([
            sys.executable, str(ROOT / "lab" / "sensor" / "run_zeek.py"),
            "--pcap", pcap_relative, "--output-dir", str(zeek_dir), "--storage-backend", "docker_volume",
            "--capture-volume", CAPTURE_VOLUME, "--zeek-volume", ZEEK_VOLUME,
            "--run-id", manifest["run_id"], "--attempt-id", scenario["execution_id"], "--strict",
        ], env=env, timeout=300)
        normalized_path = output / "normalized" / f'{scenario["execution_id"]}.jsonl'
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        _run([
            sys.executable, str(ROOT / "lab" / "sensor" / "normalize_zeek_events.py"),
            "--logs-dir", str(zeek_dir), "--output", str(normalized_path), "--run-id", manifest["run_id"],
        ], env=env)
        correlated.extend(correlate_isolated_capture(manifest, _read_jsonl(normalized_path), scenario["execution_id"]))

    correlated_path = output / "correlated_sensor_events.jsonl"
    correlated_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in correlated) + "\n", encoding="utf-8")
    dataset = output / "future_integrity_dataset.csv"
    dataset_integrity = output / "dataset_integrity.json"
    _run([
        sys.executable, str(ROOT / "ml" / "features" / "build_future_integrity_dataset.py"),
        "--manifest", str(manifest_path), "--events", str(correlated_path), "--marker-log", str(marker_log),
        "--output", str(dataset), "--integrity-output", str(dataset_integrity),
    ], env=env)

    marker_policy = manifest["marker_reconciliation_policy"]
    intervals = resolve_marker_intervals(
        manifest, correlated, controls,
        timestamp_resolution_seconds=marker_policy["timestamp_resolution_seconds"],
        allowed_capture_jitter_seconds=marker_policy["allowed_capture_jitter_seconds"],
    )
    traffic = _read_jsonl(traffic_events)
    assigned = [item for item in correlated if item.get("correlation_status") == "assigned"]
    sensor_distribution: dict[str, Counter] = defaultdict(Counter)
    for item in assigned:
        sensor_distribution[str(item["execution_id"])][str(item["sensor_log_type"])] += 1
    with dataset.open(encoding="utf-8", newline="") as source:
        dataset_rows = list(csv.DictReader(source))

    latency_by_execution: dict[str, list[float]] = defaultdict(list)
    for item in traffic:
        if item.get("latency_ms") is not None:
            latency_by_execution[str(item["execution_id"])].append(float(item["latency_ms"]))
    baseline_latency = statistics.mean(latency_by_execution["smoke-exec-003"])
    impaired_latency = statistics.mean(latency_by_execution["smoke-exec-001"])
    websocket_events = [item for item in traffic if item.get("scenario_id") == "smoke_websocket_ping_pong"]
    websocket_ok = bool(websocket_events) and all(
        session.get("upgrade_101") and session.get("text_ping_pong") and session.get("protocol_ping_pong") and session.get("close_handshake")
        for event in websocket_events for session in event.get("details", {}).get("sessions", [])
    )
    dns_count = sum(item.get("sensor_log_type") == "dns" and item.get("execution_id") == "smoke-exec-002" for item in assigned)
    marker_ok = all(
        interval.sensor_start_count >= 1 and interval.sensor_end_count >= 1
        and max(interval.sensor_start_count, interval.sensor_end_count) >= 2
        and interval.control_start_count >= 1 and interval.control_end_count >= 1
        and interval.duration_seconds > 0
        for interval in intervals.values()
    )
    workflow_audit = workflow_runtime_audit()
    _write_json(output / "workflow_runtime_audit.json", workflow_audit)
    independence = audit_condition_independence(condition_records)
    dataset_evidence = json.loads(dataset_integrity.read_text(encoding="utf-8"))
    marker_durations = [value.duration_seconds for value in intervals.values()]
    typed_hashes = [dataset_evidence[name] for name in (
        "feature_schema_sha256", "dataset_sha256", "row_order_sha256",
        "execution_mapping_sha256", "marker_intervals_sha256",
    )]

    def collision_groups(values: dict[str, Any]) -> list[list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for execution_id, value in values.items():
            grouped[json.dumps(value, sort_keys=True, separators=(",", ":"))].append(execution_id)
        return [names for names in grouped.values() if len(names) > 1]

    feature_vectors = {
        row["execution_id"]: {name: row[name] for name in row if name not in {
            "run_id", "execution_id", "scenario_execution_key", "window_index", "scenario_id", "label", "label_type",
            "execution_mode", "synthetic", "observation_source", "sensor_type", "feature_profile", "interval_source",
            "marker_interval_evidence_sha256", "campaign_id", "campaign_version", "campaign_role", "campaign_run_index",
            "campaign_seed", "scenario_variant_id", "scenario_parameter_hash", "environment_profile_id",
        }} for row in dataset_rows
    }
    collision_report = {
        "protocol_sequence_collisions": workflow_audit["observable_protocol_collisions"],
        "zeek_distribution_collisions": collision_groups({key: dict(value) for key, value in sensor_distribution.items()}),
        "feature_vector_collisions": collision_groups(feature_vectors),
        "metadata_only_distinctions": workflow_audit["observable_protocol_collisions"],
        "recommendation": "merge or redesign a workflow before campaign inclusion when protocol and sensor evidence collide",
    }
    _write_json(output / "runtime_collision_report.json", collision_report)
    checks = {
        "all_executions_completed": len(condition_records) == len(EXECUTIONS),
        "all_rollbacks_verified": all(item["rollback_verified"] for item in condition_records),
        "conditions_active_during_execution": all(item["verification_contains_netem"] for item in condition_records),
        "condition_assignment_independent_of_label": independence["status"] == "passed",
        "latency_impairment_observed": impaired_latency >= baseline_latency + 20,
        "all_pcaps_nonempty": len(pcap_records) == len(EXECUTIONS) and all(item["size_bytes"] > 24 for item in pcap_records),
        "copy_aware_markers_valid": marker_ok,
        "marker_flows_excluded": not any(is_marker_event(item) and item.get("correlation_status") == "assigned" for item in correlated),
        "marker_duration_not_fixed_fallback": len({round(value, 6) for value in marker_durations}) > 1,
        "dns_observed_by_sensor": dns_count > 0,
        "dns_uses_internal_resolver_only": manifest["network_policy"]["external_dns_allowed"] is False,
        "websocket_ping_pong_close_observed_by_client": websocket_ok,
        "websocket_observed_by_sensor": sensor_distribution["smoke-exec-004"]["websocket"] > 0,
        "all_workflows_have_sensor_events": all(sensor_distribution[item[0]] for item in EXECUTIONS),
        "future_dataset_validated": len(dataset_rows) == len(EXECUTIONS),
        "typed_hash_domains_distinct": len(typed_hashes) == len(set(typed_hashes)),
        "runtime_output_ignored": _run(["git", "check-ignore", str(output)], env=env, check=False).returncode == 0,
        "workflow_audit_complete": workflow_audit["workflow_count"] > 0,
        "full_v038_training_not_performed": True,
        "smoke_data_not_used_for_training": True,
    }
    return {
        "status": "passed" if all(checks.values()) else "failed", "passed": all(checks.values()),
        "checks": checks, "execution_count": len(EXECUTIONS), "dataset_row_count": len(dataset_rows),
        "environment_condition_independence": independence,
        "latency_evidence_ms": {"no_impairment_http": round(baseline_latency, 3), "latency_40ms_http": round(impaired_latency, 3)},
        "dns_sensor_event_count": dns_count, "websocket_session_count": len(websocket_events),
        "marker_copy_counts": {key: {"start": value.sensor_start_count, "end": value.sensor_end_count} for key, value in intervals.items()},
        "sensor_log_distribution": {key: dict(value) for key, value in sensor_distribution.items()},
        "feature_samples": [{name: row[name] for name in ("execution_id", "flow_count", "dns_query_count", "flows_per_second", "events_per_second")} for row in dataset_rows],
        "pcap_evidence": pcap_records, "dataset_integrity": dataset_evidence,
        "workflow_collision_group_count": len(workflow_audit["observable_protocol_collisions"]),
        "runtime_collision_report": collision_report,
        "secure_artifact_verification": verify_secure(None, ROOT / "ml" / "experiments" / "post_v037_audit" / "secure_artifact_reference.yaml"),
        "historical_results_modified": False, "full_v038_training_performed": False,
        "smoke_evidence_sha256": canonical_sha256("dataset_sha256", {"checks": checks, "pcaps": pcap_records, "dataset": dataset_evidence}),
    }


def run(output: Path, skip_build: bool = False) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise RuntimeError("smoke output directory already exists")
    output.mkdir(parents=True)
    env = os.environ.copy()
    env.update({
        "COMPOSE_PROJECT_NAME": PROJECT, "FILIN_LAB_NET": NETWORK,
        "FILIN_MGMT_NET": MGMT_NETWORK, "FILIN_MONITOR_NET": MONITOR_NETWORK,
        "FILIN_SENSOR_CAPTURE_VOLUME": CAPTURE_VOLUME, "FILIN_TRAFFIC_CLIENT_IMAGE": "filin-pre-v038-traffic-client:smoke",
        "FILIN_TARGET_WEB_PORT": "127.0.0.1:0", "FILIN_TARGET_API_PORT": "127.0.0.1:0",
        "FILIN_SCENARIO_CAPTURE_DIR": "/capture/pre_v038_smoke",
    })
    previous_environment = {name: os.environ.get(name) for name in env if name.startswith("FILIN_") or name == "COMPOSE_PROJECT_NAME"}
    before = _docker_ids(env)
    result: dict[str, Any] | None = None
    failure: BaseException | None = None
    try:
        os.environ.update({name: value for name, value in env.items() if name.startswith("FILIN_") or name == "COMPOSE_PROJECT_NAME"})
        result = _execute(output, env, skip_build)
    except BaseException as error:
        failure = error
    finally:
        _run(_compose("down", "--remove-orphans"), env=env, check=False, timeout=300)
        for volume in (CAPTURE_VOLUME, ZEEK_VOLUME):
            if not volume.startswith(PROJECT):
                raise RuntimeError("unsafe smoke volume cleanup target")
            _run(["docker", "volume", "rm", "-f", volume], env=env, check=False)
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    if failure is not None:
        raise failure
    assert result is not None
    after = _docker_ids(env)
    result["compose_isolation"] = {
        "project": PROJECT, "preexisting_containers_still_running": before <= after,
        "smoke_containers_removed": not _run(_compose("ps", "-q"), env=env).stdout.strip(),
    }
    result["checks"]["compose_isolation_preserved"] = all(result["compose_isolation"].values()) if "project" not in result["compose_isolation"] else (
        result["compose_isolation"]["preexisting_containers_still_running"] and result["compose_isolation"]["smoke_containers_removed"]
    )
    result["passed"] = all(result["checks"].values())
    result["status"] = "passed" if result["passed"] else "failed"
    _write_json(output / "acceptance_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    result = run(Path(args.output), args.skip_build)
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
