"""Sequential, resumable execution of the v0.3.3 Docker environment campaign."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab" / "tools"))
sys.path.insert(0, str(ROOT / "lab" / "campaigns"))
sys.path.insert(0, str(ROOT / "ml" / "features"))

from environment_campaign import build_run_manifest, load_campaign, run_is_complete
from label_writer import save_manifest
from scenario_runner import execute_manifest
from validators import validate_dataset


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def docker(command: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT / "lab" / "docker", env=env, check=check, capture_output=True, text=True, encoding="utf-8")


def docker_with_retry(command: list[str], env: dict[str, str], attempts: int = 3) -> None:
    last: subprocess.CalledProcessError | None = None
    for _ in range(attempts):
        try:
            docker(command, env=env)
            return
        except subprocess.CalledProcessError as error:
            last = error
            time.sleep(2)
    assert last is not None
    raise last


def capture_volume_name(run_id: str) -> str:
    return "filin_v033_" + run_id.lower().replace("-", "_")


def build_status(run: dict[str, Any], error: Exception | None = None) -> dict[str, Any]:
    result = {"run_id": run["run_id"], "environment_group": run["group"], "seed": run["random_seed"]}
    if error is None:
        result.update({name: "success" for name in ("run_status", "capture_audit_status", "correlation_audit_status", "aggregation_consistency_status", "sensor_validator_status", "dataset_status")})
    else:
        result.update({"run_status": "failed", "error_type": type(error).__name__, "error_message": str(error)})
    return result


def execute_run(campaign: dict[str, Any], run: dict[str, Any], output_root: Path) -> dict[str, Any]:
    run_dir = output_root / "runs" / run["run_id"]
    # Preserve an interrupted or failed capture for diagnosis before creating a
    # new attempt.  Successful runs are filtered by run_is_complete in main.
    if (run_dir / "scenario_manifest.yaml").exists():
        attempts = run_dir / "attempts"
        attempts.mkdir(exist_ok=True)
        number = len(list(attempts.glob("attempt_*"))) + 1
        archived = attempts / f"attempt_{number:03d}_failed"
        archived.mkdir()
        for child in list(run_dir.iterdir()):
            if child.name != "attempts":
                shutil.move(str(child), archived / child.name)
    sensor_dir = run_dir / "sensor"
    sensor_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "scenario_manifest.yaml"
    manifest = build_run_manifest(campaign, run, ROOT / "lab" / "scenarios")
    save_manifest(manifest_path, manifest)
    volume = capture_volume_name(run["run_id"])
    env = {**os.environ, "FILIN_SENSOR_CAPTURE_VOLUME": volume}
    compose = ROOT / "lab" / "docker" / "docker-compose.lab.yml"
    # A timeout may leave the sidecar alive with a previous volume binding.
    # Stop it first; diagnostic PCAPs are retained in their named volumes.
    docker(["docker", "compose", "-f", str(compose), "stop", "sensor-capture"], env=env, check=False)
    docker_with_retry(["docker", "compose", "-f", str(compose), "up", "-d", "--build", "target-web", "target-api", "control-api", "target-ssh-sim", "traffic-client"], env)
    time.sleep(1.0)
    docker_with_retry(["docker", "compose", "-f", str(compose), "up", "-d", "sensor-capture"], env)
    time.sleep(1.0)
    try:
        completed, failed, skipped = execute_manifest(
            manifest_path, allow_dry_run_manifest=True, respect_schedule=False, max_runtime_seconds=900,
            mock=False, compose_file=compose, compose_project_dir=ROOT / "lab" / "docker", time_scale=0.05,
            random_seed=int(run["random_seed"]),
        )
        if failed or skipped or completed != 17:
            raise RuntimeError(f"Выполнено {completed}/17; failed={failed}; skipped={skipped}.")
        # tcpdump writes asynchronously; let the final end marker reach the
        # PCAP before the capture sidecar is stopped.
        time.sleep(1.0)
    finally:
        docker(["docker", "compose", "-f", str(compose), "stop", "sensor-capture"], env=env, check=False)
    internal = f"runs/{run['run_id']}/attempt_001/capture.pcap"
    docker(["docker", "run", "--rm", "-v", f"{volume}:/captures", "busybox", "sh", "-c", f"mkdir -p /captures/runs/{run['run_id']}/attempt_001 && cp /captures/capture.pcap /captures/{internal}"])
    sys.executable
    subprocess.run([sys.executable, str(ROOT / "lab" / "sensor" / "run_zeek.py"), "--pcap", internal, "--output-dir", str(sensor_dir / "zeek"), "--storage-backend", "docker_volume", "--capture-volume", volume, "--run-id", run["run_id"], "--strict"], cwd=ROOT, check=True)
    events = sensor_dir / "zeek_events.jsonl"
    normalized = sensor_dir / "normalized_sensor_events.jsonl"
    subprocess.run([sys.executable, str(ROOT / "lab" / "sensor" / "normalize_zeek_events.py"), "--logs-dir", str(sensor_dir / "zeek"), "--output", str(events), "--run-id", run["run_id"]], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "lab" / "sensor" / "correlate_sensor_events.py"), "--manifest", str(manifest_path), "--events", str(events), "--output", str(normalized), "--strict"], cwd=ROOT, check=True)
    dataset = output_root / "datasets" / f"windows_network_sensor_v0_3_{run['run_id']}.csv"
    subprocess.run([sys.executable, str(ROOT / "ml" / "features" / "build_network_sensor_dataset.py"), "--manifest", str(manifest_path), "--events", str(normalized), "--output", str(dataset)], cwd=ROOT, check=True)
    validate_dataset(dataset, kind="windows", feature_profile="network_sensor_v0_3")
    pcap_sha = subprocess.run(["docker", "run", "--rm", "-v", f"{volume}:/captures:ro", "busybox", "sha256sum", f"/captures/{internal}"], check=True, capture_output=True, text=True).stdout.split()[0]
    state = {"run": run, "pcap_volume": volume, "pcap_internal_path": internal, "pcap_sha256": pcap_sha, "manifest_sha256": hash_file(manifest_path), "normalized_sensor_events_sha256": hash_file(normalized), "dataset_sha256": hash_file(dataset), "assigned_sensor_events": sum(1 for line in normalized.read_text(encoding="utf-8").splitlines() if '"correlation_status": "assigned"' in line)}
    atomic_json(run_dir / "environment_run_integrity.json", state)
    return build_status(run)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v0.3.3 environment campaign sequentially.")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--output-root", default="lab/output")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-ids", nargs="*")
    args = parser.parse_args()
    campaign = load_campaign(Path(args.campaign))
    root = Path(args.output_root)
    status_path = root / "campaigns" / "filin_v0_3_3_environment" / "status.json"
    status: dict[str, Any] = json.loads(status_path.read_text(encoding="utf-8")) if args.resume and status_path.exists() else {}
    for run in campaign["runs"]:
        run_id = run["run_id"]
        if args.run_ids and run_id not in args.run_ids:
            continue
        if args.resume and isinstance(status.get(run_id), dict) and run_is_complete(status[run_id]):
            continue
        try:
            status[run_id] = execute_run(campaign, run, root)
        except Exception as error:
            status[run_id] = build_status(run, error)
        atomic_json(status_path, status)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    selected = [run for run in campaign["runs"] if not args.run_ids or run["run_id"] in args.run_ids]
    if args.strict and not all(isinstance(status.get(run["run_id"]), dict) and run_is_complete(status[run["run_id"]]) for run in selected):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
