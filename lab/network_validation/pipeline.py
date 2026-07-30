from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .capture import build_capture_manifest, validate_capture_set
from .common_client import CLIENT_IDENTITY
from .contracts import load_json, write_canonical
from .feature_adapter import SessionFeatureAdapter
from .parameter_verification import observations_from_zeek, verify_parameters

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = Path(__file__).with_name("compose.yaml")


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
            capture = subprocess.run(
                command + ["run", "-d", "--no-deps", "sensor-capture", "-i", scenario["capture_policy"]["interface"],
                           "-B", "4096", "--immediate-mode", "-U", "-Z", "root",
                           "-w", f"/capture/{scenario_name}.pcap", *shlex.split(scenario["capture_policy"]["bpf"])],
                cwd=COMPOSE.parent, check=True, capture_output=True, text=True,
            ).stdout.strip()
            capture_containers.append(capture)
            time.sleep(1)
            subprocess.run(command + ["exec", "-T", "common-client", "python", "-m", "lab.network_validation.common_client", "--scenario", f"/config/{scenario_name}.json", "--target-map", target_map, "--output-dir", f"/output/{scenario_name}", "--capture-id", scenario_name], cwd=COMPOSE.parent, check=True)
            subprocess.run(["docker", "stop", capture], check=True, capture_output=True)
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
                            "zeek/zeek:7.0.5", "sh", "-lc", script], check=True)
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
            subprocess.run(command + ["down", "--volumes"], cwd=COMPOSE.parent, check=False, capture_output=True)
