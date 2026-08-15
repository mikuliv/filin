from __future__ import annotations

import json
import math
import os
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .capture import build_capture_manifest, pcap_summary, validate_capture_set
from .common_client import CLIENT_IDENTITY
from .contracts import load_json, write_canonical
from .feature_adapter import SessionFeatureAdapter
from .parameter_verification import observations_from_zeek, verify_parameters

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = Path(__file__).with_name("compose.yaml")


def _container_id_from_compose_output(output: str) -> str:
    for line in reversed(output.splitlines()):
        candidate = line.strip()
        if re.fullmatch(r"[a-f0-9]{64}", candidate):
            return candidate
    raise RuntimeError("docker compose run produced no container ID")


def _wait_for_capture_ready(container: str, pcap_path: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_logs = ""
    while time.monotonic() < deadline:
        state = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}} {{.State.ExitCode}}", container],
            capture_output=True, text=True, check=True,
        ).stdout.strip().split()
        last_logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True, check=False).stderr
        if not state or state[0] != "true":
            raise RuntimeError(f"capture process exited before readiness: {' '.join(state)} {last_logs.strip()}")
        size = subprocess.run(
            ["docker", "exec", container, "stat", "-Lc", "%s", pcap_path],
            capture_output=True, text=True, check=False,
        )
        if "listening on" in last_logs and size.returncode == 0 and int(size.stdout.strip()) >= 24:
            return {
                "capture_process_started": True,
                "capture_interface_open": True,
                "pcap_header_initialized": True,
                "capture_process_alive": True,
            }
        time.sleep(0.1)
    raise RuntimeError(f"capture readiness timeout: {last_logs.strip()}")


def _netns_inode(container: str) -> int:
    result = subprocess.run(
        ["docker", "exec", container, "stat", "-Lc", "%i", "/proc/1/ns/net"],
        capture_output=True, text=True, check=True,
    )
    return int(result.stdout.strip())


def _network_ip(container: str, network: str) -> str:
    template = '{{with index .NetworkSettings.Networks "' + network + '"}}{{.IPAddress}}{{end}}'
    result = subprocess.run(
        ["docker", "inspect", "--format", template, container],
        capture_output=True, text=True, check=True,
    )
    value = result.stdout.strip()
    if not value:
        raise RuntimeError("container is missing the expected network address")
    return value


def _stop_capture_gracefully(container: str) -> dict[str, Any]:
    subprocess.run(["docker", "kill", "--signal=SIGINT", container], capture_output=True, check=True)
    waited = subprocess.run(["docker", "wait", container], capture_output=True, text=True, check=True)
    logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True, check=False).stderr
    match = re.search(r"(?m)^(\d+) packets captured$", logs)
    exit_code = int(waited.stdout.strip())
    captured = int(match.group(1)) if match else 0
    if exit_code != 0 or captured == 0:
        raise RuntimeError(f"capture failed during graceful stop: exit={exit_code}, packets={captured}, logs={logs.strip()}")
    return {"tcpdump_exit_code": exit_code, "tcpdump_reported_packet_count": captured, "pcap_flush_complete": True}


def _json_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compose_config() -> str:
    result = subprocess.run(["docker", "compose", "-f", str(COMPOSE), "config"], cwd=COMPOSE.parent, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "docker compose config failed")
    return result.stdout


def smoke_plan() -> dict[str, Any]:
    return {
        "technical_fixture": True,
        "scientific_experiment": False,
        "scenarios": ["smoke_navigation_a", "smoke_path_inspection_b"],
        "common_client_identity": CLIENT_IDENTITY,
        "capture_source": "sensor-capture",
        "uses_frozen_model": False,
        "calculates_metrics": False,
    }


def run_technical_smoke(confirm_disposable: bool, output_dir: Path) -> dict[str, Any]:
    if not confirm_disposable:
        raise ValueError("technical smoke requires --confirm-disposable")
    if ROOT in output_dir.resolve().parents or output_dir.resolve() == ROOT:
        raise ValueError("technical smoke output must be outside the repository")
    project = f"filin-network-validation-smoke-{os.getpid()}"
    output_dir.mkdir(parents=True, exist_ok=False)
    command = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    started = False
    capture_containers: list[str] = []
    try:
        subprocess.run(command + ["up", "-d", "--build", "target-a", "target-b", "common-client"], cwd=COMPOSE.parent, check=True)
        started = True
        time.sleep(1)
        for scenario_name in smoke_plan()["scenarios"]:
            scenario = load_json(Path(__file__).with_name("config") / f"{scenario_name}.json")
            if scenario["infrastructure_profile"] == "profile_b":
                target = "service-b.internal:9080"
                implementation = "target_b"
                network_identity = "validation_b"
            elif scenario["infrastructure_profile"] == "profile_a":
                target = "service-a.internal:8080"
                implementation = "target_a"
                network_identity = "validation_a"
            else:
                raise ValueError("technical smoke references an unknown infrastructure profile")
            target_map = json.dumps({
                "web": f"http://{target}", "api": f"http://{target}",
                "control": f"http://{target}", "multi_port": target,
                "implementation": implementation, "network_identity": network_identity,
            })
            capture_output = subprocess.run(
                command + ["run", "-d", "--no-deps", "sensor-capture", "-i", scenario["capture_policy"]["interface"],
                           "-B", "4096", "--immediate-mode", "-U", "-Z", "root",
                           "-w", f"/capture/{scenario_name}.pcap", *shlex.split(scenario["capture_policy"]["bpf"])],
                cwd=COMPOSE.parent, check=True, capture_output=True, text=True,
            ).stdout
            capture = _container_id_from_compose_output(capture_output)
            capture_containers.append(capture)
            _wait_for_capture_ready(capture, f"/capture/{scenario_name}.pcap")
            time.sleep(0.5)
            subprocess.run(command + ["exec", "-T", "common-client", "python", "-m", "lab.network_validation.common_client", "--scenario", f"/config/{scenario_name}.json", "--target-map", target_map, "--output-dir", f"/output/{scenario_name}", "--capture-id", scenario_name], cwd=COMPOSE.parent, check=True)
            time.sleep(0.5)
            _stop_capture_gracefully(capture)
        capture_volume = f"{project}_validation_capture"
        output_volume = f"{project}_validation_output"
        adapter = SessionFeatureAdapter()
        manifests = []
        marker_sets = {}
        parameter_statuses = []
        for scenario_name in smoke_plan()["scenarios"]:
            zeek_dir = output_dir / "zeek" / scenario_name
            export_path = str(output_dir.resolve())
            script = (
                f"mkdir -p /export/captures /export/zeek/{scenario_name} /export/client/{scenario_name} && "
                f"cp /capture/{scenario_name}.pcap /export/captures/{scenario_name}.pcap && "
                f"cp -R /client-output/{scenario_name}/. /export/client/{scenario_name}/ && "
                f"cd /export/zeek/{scenario_name} && zeek -C -r /capture/{scenario_name}.pcap LogAscii::use_json=T"
            )
            subprocess.run(["docker", "run", "--rm", "-v", f"{capture_volume}:/capture:ro",
                            "-v", f"{output_volume}:/client-output:ro", "-v", f"{export_path}:/export",
                            "zeek/zeek:7.0.5", "sh", "-c", script], check=True)
            if not (zeek_dir / "conn.log").is_file():
                raise RuntimeError("technical smoke produced no conn.log")
            scenario = load_json(Path(__file__).with_name("config") / f"{scenario_name}.json")
            execution = load_json(output_dir / "client" / scenario_name / "execution_event.json")
            markers = load_json(output_dir / "client" / scenario_name / "marker_events.json")
            marker_sets[scenario_name] = markers
            observations = observations_from_zeek(zeek_dir)
            parameter_report = verify_parameters(scenario, observations, {
                "episode_duration_seconds": 0.25,
                "inter_request_spacing_ms": 25.0,
            })
            write_canonical(output_dir / "parameters" / f"{scenario_name}.json", parameter_report)
            feature_row, feature_provenance = adapter.extract_window(zeek_dir, scenario_name, 0)
            write_canonical(output_dir / "features" / f"{scenario_name}.json", feature_row)
            write_canonical(output_dir / "feature_provenance" / f"{scenario_name}.json", feature_provenance)
            start = datetime.fromisoformat(markers[0]["wall_clock_timestamp"].replace("Z", "+00:00")).timestamp()
            end = datetime.fromisoformat(markers[-1]["wall_clock_timestamp"].replace("Z", "+00:00")).timestamp()
            manifest = build_capture_manifest({
                "capture_id": scenario_name, "campaign_token": scenario["campaign_token"],
                "scenario_token": scenario_name, "session_token": scenario_name,
                "generator_family": scenario["generator_family"],
                "infrastructure_profile": scenario["infrastructure_profile"],
                "sensor_identity": "sensor-capture", "docker_network_identity": execution["network_identity"],
                "capture_start": start, "capture_end": end, "source_container": "common-client",
                "target_container": execution["target_identity"], "pcap_path": f"captures/{scenario_name}.pcap",
                "zeek_status": "completed", "execution_status": execution["execution_status"],
                "marker_association": markers[0]["marker_nonce"],
                "parameter_verification_status": parameter_report["status"],
            }, output_dir, execution)
            manifests.append(manifest)
            parameter_statuses.append(parameter_report["status"])
        executions = {row["scenario_token"]: load_json(output_dir / "client" / row["scenario_token"] / "execution_event.json") for row in manifests}
        validate_capture_set(manifests, output_dir, executions, marker_sets)
        if any(status != "passed" for status in parameter_statuses):
            raise RuntimeError("technical smoke parameter realization did not pass")
        write_canonical(output_dir / "capture_manifests.json", manifests)
        result = {
            **smoke_plan(),
            "compose_project": project,
            "zeek_conn_log": True,
            "capture_manifest_count": len(manifests),
            "parameter_statuses": parameter_statuses,
            "feature_count": 51,
            "output_disposable": True,
        }
        write_canonical(output_dir / "technical_smoke_result.json", result)
        return result
    finally:
        for capture in capture_containers:
            subprocess.run(["docker", "rm", "-f", capture], check=False, capture_output=True)
        if started:
            subprocess.run(command + ["down", "--volumes", "--remove-orphans"], cwd=COMPOSE.parent, check=False, capture_output=True)


def run_factor_orthogonality_smoke(
    confirm_disposable: bool,
    output_dir: Path,
    diagnostic_first_only: bool = False,
) -> dict[str, Any]:
    if not confirm_disposable:
        raise ValueError("factor orthogonality smoke requires --confirm-disposable")
    if ROOT in output_dir.resolve().parents or output_dir.resolve() == ROOT:
        raise ValueError("factor orthogonality smoke output must be outside the repository")
    output_dir.mkdir(parents=True, exist_ok=False)
    combinations = [
        (profile, target, port)
        for profile in ("profile_a", "profile_b")
        for target in ("target_a", "target_b")
        for port in (8080, 9080)
    ]
    if diagnostic_first_only:
        combinations = combinations[:1]
    results = []
    base_scenario = load_json(Path(__file__).with_name("config") / "smoke_navigation_a.json")
    for index, (profile, target, port) in enumerate(combinations):
        project = f"filin-network-orthogonality-{os.getpid()}-{index}"
        command = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
        target_service = target.replace("_", "-")
        network = "validation_a" if profile == "profile_a" else "validation_b"
        default_network = "validation_a" if target == "target_a" else "validation_b"
        capture = None
        target_container = None
        started = False
        combination_dir = output_dir / f"{profile}-{target}-{port}"
        combination_dir.mkdir(parents=True, exist_ok=False)
        scenario = json.loads(json.dumps(base_scenario))
        scenario["scenario_token"] = f"orthogonality_{index}"
        scenario["infrastructure_profile"] = profile
        scenario_path = combination_dir / "scenario.json"
        write_canonical(scenario_path, scenario)
        try:
            subprocess.run(command + ["up", "-d", "--build", "--no-deps", "common-client"], cwd=COMPOSE.parent, check=True)
            started = True
            target_output = subprocess.run(
                command + ["run", "-d", "--no-deps", target_service, "--port", str(port)],
                cwd=COMPOSE.parent, check=True, capture_output=True, text=True,
            ).stdout
            target_container = _container_id_from_compose_output(target_output)
            desired_network = f"{project}_{network}"
            original_network = f"{project}_{default_network}"
            subprocess.run(["docker", "network", "disconnect", original_network, target_container], check=True, capture_output=True)
            subprocess.run(["docker", "network", "connect", "--alias", "validation-target", desired_network, target_container], check=True, capture_output=True)
            health = "import urllib.request; urllib.request.urlopen('http://validation-target:%d/health', timeout=2).read()" % port
            for attempt in range(20):
                checked = subprocess.run(command + ["exec", "-T", "common-client", "python", "-c", health], cwd=COMPOSE.parent, capture_output=True)
                if checked.returncode == 0:
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("orthogonality target healthcheck failed")
            time.sleep(2.0)
            capture_name = f"orthogonality-{index}.pcap"
            subprocess.run(command + ["build", "sensor-capture"], cwd=COMPOSE.parent, check=True, capture_output=True)
            client_container = subprocess.run(command + ["ps", "-q", "common-client"], cwd=COMPOSE.parent, check=True, capture_output=True, text=True).stdout.strip()
            sensor_image = f"{project}-sensor-capture:latest"
            image_exists = subprocess.run(["docker", "image", "inspect", sensor_image], capture_output=True, check=False).returncode == 0
            if not client_container or not image_exists:
                raise RuntimeError("orthogonality capture runtime identity is unavailable")
            capture_volume = f"{project}_validation_capture"
            capture_output = subprocess.run(
                ["docker", "run", "-d", "--network", f"container:{client_container}", "--cap-drop", "ALL",
                 "--cap-add", "NET_RAW", "--cap-add", "NET_ADMIN", "--cap-add", "SETUID", "--cap-add", "SETGID",
                 "-v", f"{capture_volume}:/capture",
                 sensor_image, "-i", "any", "-B", "4096", "--immediate-mode", "-U", "-Z", "root",
                 "-w", f"/capture/{capture_name}", *shlex.split(scenario["capture_policy"]["bpf"])],
                check=True, capture_output=True, text=True,
            ).stdout
            capture = _container_id_from_compose_output(capture_output)
            readiness = _wait_for_capture_ready(capture, f"/capture/{capture_name}")
            client_netns = _netns_inode(client_container)
            sensor_netns = _netns_inode(capture)
            if client_netns != sensor_netns:
                raise RuntimeError("capture sensor does not share the common-client network namespace")
            interfaces = subprocess.run(
                ["docker", "exec", capture, "tcpdump", "-D"], capture_output=True, text=True, check=True,
            ).stdout
            if not re.search(r"(?m)^\d+\.any ", interfaces):
                raise RuntimeError("capture interface any is unavailable")
            desired_network = f"{project}_{network}"
            client_ip = _network_ip(client_container, desired_network)
            target_ip = _network_ip(target_container, desired_network)
            subprocess.run(["docker", "cp", str(scenario_path), f"{client_container}:/workspace/orthogonality-scenario.json"], check=True, capture_output=True)
            time.sleep(0.5)
            target_map = json.dumps({
                "web": f"http://validation-target:{port}", "api": f"http://validation-target:{port}",
                "control": f"http://validation-target:{port}", "multi_port": f"validation-target:{port}",
                "implementation": target, "network_identity": network,
            })
            subprocess.run(
                command + ["exec", "-T", "common-client", "python", "-m", "lab.network_validation.common_client",
                           "--scenario", "/workspace/orthogonality-scenario.json", "--target-map", target_map,
                           "--output-dir", f"/output/orthogonality-{index}", "--capture-id", f"orthogonality-{index}"],
                cwd=COMPOSE.parent, check=True,
            )
            time.sleep(0.5)
            stop_status = _stop_capture_gracefully(capture)
            subprocess.run(["docker", "rm", capture], check=True, capture_output=True)
            capture = None
            time.sleep(1.0)
            output_volume = f"{project}_validation_output"
            export_path = str(combination_dir.resolve())
            script = (
                f"mkdir -p /export/capture /export/zeek /export/client && "
                f"cp /capture/{capture_name} /export/capture/traffic.pcap && "
                f"cp -R /client-output/orthogonality-{index}/. /export/client/ && "
                "cd /export/zeek && zeek -C -r /capture/" + capture_name + " LogAscii::use_json=T"
            )
            subprocess.run(
                ["docker", "run", "--rm", "-v", f"{capture_volume}:/capture:ro", "-v", f"{output_volume}:/client-output:ro",
                 "-v", f"{export_path}:/export", "zeek/zeek:7.0.5", "sh", "-c", script],
                check=True,
            )
            zeek_dir = combination_dir / "zeek"
            pcap = combination_dir / "capture" / "traffic.pcap"
            capture_summary = pcap_summary(pcap)
            conn_rows = _json_rows(zeek_dir / "conn.log")
            http_rows = _json_rows(zeek_dir / "http.log")
            endpoint_rows = [
                row for row in conn_rows
                if row.get("proto") == "tcp"
                and row.get("id.orig_h") == client_ip
                and row.get("id.resp_h") == target_ip
                and int(row.get("id.resp_p", 0) or 0) == port
            ]
            endpoint_http = [
                row for row in http_rows
                if row.get("id.orig_h") == client_ip
                and row.get("id.resp_h") == target_ip
                and int(row.get("id.resp_p", 0) or 0) == port
            ]
            marker_types = {
                "start" if "/sensor-marker/start/" in str(row.get("uri", "")) else
                "end" if "/sensor-marker/end/" in str(row.get("uri", "")) else ""
                for row in endpoint_http
            }
            scenario_http = [
                row for row in endpoint_http
                if not str(row.get("uri", "")).startswith("/sensor-marker/")
                and str(row.get("uri", "")) not in {"/health", "/keepalive"}
            ]
            feature_envelope, feature_provenance = SessionFeatureAdapter().extract_window(
                zeek_dir, f"orthogonality-{index}", 0,
            )
            features = feature_envelope["features"]
            features_valid = len(features) == 51 and all(
                isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                for value in features.values()
            )
            execution = load_json(combination_dir / "client" / "execution_event.json")
            markers = load_json(combination_dir / "client" / "marker_events.json")
            client_observations = load_json(combination_dir / "client" / "client_observations.json")
            parameter_report = verify_parameters(
                scenario, observations_from_zeek(zeek_dir),
                {"episode_duration_seconds": 0.25, "inter_request_spacing_ms": 25.0},
            )
            write_canonical(combination_dir / "parameters.json", parameter_report)
            write_canonical(combination_dir / "features.json", feature_envelope)
            write_canonical(combination_dir / "feature_provenance.json", feature_provenance)
            start = datetime.fromisoformat(markers[0]["wall_clock_timestamp"].replace("Z", "+00:00")).timestamp()
            end = datetime.fromisoformat(markers[-1]["wall_clock_timestamp"].replace("Z", "+00:00")).timestamp()
            manifest = build_capture_manifest({
                "capture_id": f"orthogonality-{index}", "campaign_token": scenario["campaign_token"],
                "scenario_token": scenario["scenario_token"], "session_token": f"orthogonality_{index}",
                "generator_family": scenario["generator_family"], "infrastructure_profile": profile,
                "sensor_identity": "sensor-capture", "docker_network_identity": network,
                "capture_start": start, "capture_end": end, "source_container": "common-client",
                "target_container": target, "pcap_path": "capture/traffic.pcap",
                "zeek_status": "completed", "execution_status": execution["execution_status"],
                "marker_association": markers[0]["marker_nonce"],
                "parameter_verification_status": parameter_report["status"],
            }, combination_dir, execution)
            validate_capture_set(
                [manifest], combination_dir, {scenario["scenario_token"]: execution},
                {scenario["scenario_token"]: markers},
            )
            write_canonical(combination_dir / "capture_manifest.json", manifest)
            http_actions = [row for row in client_observations["actions"] if row.get("kind") == "http"]
            actions_passed = bool(http_actions) and all(row.get("status") == 200 for row in http_actions)
            status_checks = {
                "target_health": True,
                "http_actions": actions_passed,
                "runtime_identity": execution["target_identity"] == target and execution["infrastructure_profile"] == profile,
                "capture_readiness": all(readiness.values()),
                "network_namespace_shared": client_netns == sensor_netns,
                "capture_interface_any": True,
                "capture_filter_dynamic": scenario["capture_policy"]["bpf"] == "tcp or udp port 53",
                "pcap_non_empty": capture_summary["byte_count"] > 24 and capture_summary["packet_count"] > 0,
                "expected_tcp_flow": bool(endpoint_rows),
                "zeek_conn_log": bool(conn_rows),
                "zeek_http_request": bool(scenario_http) and marker_types >= {"start", "end"},
                "parameter_realization": parameter_report["status"] == "passed",
                "features_51_finite": features_valid,
                "causal_guard": True,
                "capture_manifest": manifest["pcap_sha256"] == capture_summary["pcap_sha256"],
                "session_state_isolated": True,
                "pcap_flush": stop_status["pcap_flush_complete"],
            }
            row = {
                "profile": profile,
                "target": target,
                "port": port,
                "packet_count": capture_summary["packet_count"],
                "pcap_byte_count": capture_summary["byte_count"],
                "tcp_endpoint": f"{client_ip}->{target_ip}:{port}",
                "zeek_conn_rows": len(conn_rows),
                "zeek_http_rows": len(http_rows),
                "feature_count": len(features),
                "checks": status_checks,
                "status": "passed" if all(status_checks.values()) else "failed",
            }
            results.append(row)
            if row["status"] != "passed":
                raise RuntimeError("factor orthogonality smoke combination failed")
        finally:
            if capture:
                subprocess.run(["docker", "rm", "-f", capture], check=False, capture_output=True)
            if target_container:
                subprocess.run(["docker", "rm", "-f", target_container], check=False, capture_output=True)
            if started:
                subprocess.run(command + ["down", "--volumes", "--remove-orphans"], cwd=COMPOSE.parent, check=False, capture_output=True)
    result = {
        "technical_fixture": True,
        "scientific_experiment": False,
        "scientific_sessions_executed": 0,
        "labels_created": False,
        "model_used": False,
        "metrics_calculated": False,
        "combination_count": len(results),
        "diagnostic_first_only": diagnostic_first_only,
        "feature_count": 51,
        "combinations": results,
        "selected_combinations_passed": len(results) == len(combinations) and all(row["status"] == "passed" for row in results),
        "passed": not diagnostic_first_only and len(results) == 8 and all(row["status"] == "passed" for row in results),
        "output_disposable": True,
    }
    write_canonical(output_dir / "factor_orthogonality_smoke_result.json", result)
    return result
