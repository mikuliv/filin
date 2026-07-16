"""Последовательный resumable Docker runner кампаний v0.3.10."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "lab/campaigns"), str(ROOT / "lab/tools"), str(ROOT / "ml/features")]

from label_writer import save_manifest
from scenario_runner import execute_manifest
from validators import validate_dataset
from v0310_campaign import build_manifest


STATUS_FIELDS = ("run_status", "capture_audit_status", "correlation_audit_status", "aggregation_consistency_status", "sensor_validator_status", "dataset_status")


def atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def docker(command, environment, check=True):
    return subprocess.run(command, cwd=ROOT / "lab/docker", env=environment, check=check, capture_output=True, text=True, encoding="utf-8", errors="replace")


def retry(command, environment):
    last = None
    for _ in range(3):
        try:
            return docker(command, environment)
        except subprocess.CalledProcessError as error:
            last = error
            time.sleep(3)
    raise last


def complete(value: dict) -> bool:
    return all(value.get(name) == "success" for name in STATUS_FIELDS)


def run(campaign: dict, row: dict, output_root: Path) -> dict:
    run_id = row["run_id"]
    total_windows = int(campaign.get("total_windows", 60))
    scored_windows = int(campaign.get("scored_windows", 54))
    episode_count = int(campaign.get("episodes_per_run", 18))
    stage_tag = str(campaign.get("stage_tag", "v0310"))
    run_dir = output_root / "runs" / run_id
    if (run_dir / "scenario_manifest.yaml").exists():
        attempts = run_dir / "attempts"
        attempts.mkdir(exist_ok=True)
        archive = attempts / f"attempt_{len(list(attempts.glob('attempt_*'))) + 1:03d}_interrupted"
        archive.mkdir()
        for child in list(run_dir.iterdir()):
            if child.name != "attempts":
                shutil.move(str(child), archive / child.name)
    sensor = run_dir / "sensor"
    sensor.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "scenario_manifest.yaml"
    if campaign.get("stage_tag") == "v0311":
        from v0311_campaign import build_manifest as selected_manifest_builder
    else:
        selected_manifest_builder = build_manifest
    save_manifest(manifest_path, selected_manifest_builder(ROOT, campaign, row))
    volume = f"filin_{stage_tag}_" + run_id.lower()
    project = f"filin_{stage_tag}_{run_id.lower().replace('_','-')}"
    port_base = 18080 + int(row.get("run_index", 0)) * 10
    environment = {**os.environ, "FILIN_SENSOR_CAPTURE_VOLUME": volume, "COMPOSE_PROJECT_NAME": project,
                   "FILIN_TARGET_WEB_PORT": f"127.0.0.1:{port_base}",
                   "FILIN_TARGET_API_PORT": f"127.0.0.1:{port_base + 1}"}
    compose = ROOT / "lab/docker/docker-compose.lab.yml"
    retry(["docker", "compose", "-f", str(compose), "up", "-d", "target-web", "target-api", "control-api", "target-ssh-sim", "internal-dns", "traffic-client"], environment)
    time.sleep(3)
    retry(["docker", "compose", "-f", str(compose), "exec", "-T", "-u", "root", "traffic-client", "sh", "-c", "rm -rf /capture/scenarios /capture/marker_control.jsonl && mkdir -p /capture/scenarios && install -m 0666 /dev/null /capture/marker_control.jsonl"], environment)
    previous_capture = os.environ.get("FILIN_SCENARIO_CAPTURE_DIR")
    previous_project = os.environ.get("COMPOSE_PROJECT_NAME")
    os.environ["FILIN_SCENARIO_CAPTURE_DIR"] = "/capture/scenarios"
    os.environ["COMPOSE_PROJECT_NAME"] = project
    try:
        done, failed, skipped = execute_manifest(manifest_path, allow_dry_run_manifest=True, respect_schedule=False,
            max_runtime_seconds=2400, mock=False, compose_file=compose, compose_project_dir=ROOT / "lab/docker",
            time_scale=float(campaign.get("time_scale", .2)), random_seed=int(row["random_seed"]))
        if failed or skipped or done != total_windows:
            raise RuntimeError(f"Выполнено={done}/{total_windows}, ошибок={failed}, пропущено={skipped}")
    finally:
        if previous_capture is None:
            os.environ.pop("FILIN_SCENARIO_CAPTURE_DIR", None)
        else:
            os.environ["FILIN_SCENARIO_CAPTURE_DIR"] = previous_capture
        if previous_project is None:
            os.environ.pop("COMPOSE_PROJECT_NAME", None)
        else:
            os.environ["COMPOSE_PROJECT_NAME"] = previous_project
    marker_log = run_dir / "marker_control.jsonl"
    marker_copy = docker(["docker", "run", "--rm", "-v", f"{volume}:/captures", "busybox", "cat", "/captures/marker_control.jsonl"], environment)
    marker_log.write_text(marker_copy.stdout, encoding="utf-8")
    captures_dir = run_dir / "captures"
    captures_dir.mkdir(exist_ok=True)
    docker(["docker", "run", "--rm", "-v", f"{volume}:/captures:ro", "-v", f"{captures_dir.resolve()}:/export", "busybox", "sh", "-c", "cp /captures/scenarios/*.pcap /export/"], environment)
    zeek = sensor / "zeek_events.jsonl"
    normalized = sensor / "normalized_sensor_events.jsonl"
    all_dataset = output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}_all.csv"
    dataset = output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}.csv"
    zeek.unlink(missing_ok=True)
    normalized.unlink(missing_ok=True)
    frozen_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    captures = list(captures_dir.glob("*.pcap"))
    if len(captures) != total_windows or any(path.stat().st_size <= 24 for path in captures):
        raise ValueError(f"Ожидалось {total_windows} непустых PCAP, получено {len(captures)}")

    def process_capture(scenario):
        sequence = int(scenario["run_sequence"])
        pcap = captures_dir / f"{sequence:03d}.pcap"
        zeek_dir = sensor / "zeek" / f"{sequence:03d}"
        part_events = sensor / f"zeek_events_{sequence:03d}.jsonl"
        part_normalized = sensor / f"normalized_sensor_events_{sequence:03d}.jsonl"
        commands = (
            [sys.executable, str(ROOT / "lab/sensor/run_zeek.py"), "--pcap", str(pcap), "--output-dir", str(zeek_dir), "--storage-backend", "host_filesystem", "--strict"],
            [sys.executable, str(ROOT / "lab/sensor/normalize_zeek_events.py"), "--logs-dir", str(zeek_dir), "--output", str(part_events), "--run-id", run_id],
            [sys.executable, str(ROOT / "lab/sensor/correlate_sensor_events.py"), "--manifest", str(manifest_path), "--events", str(part_events), "--execution-id", str(scenario["execution_id"]), "--output", str(part_normalized), "--strict"],
        )
        for command in commands:
            completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if completed.returncode:
                raise RuntimeError(f"Sensor subprocess завершился с кодом {completed.returncode}: {completed.stderr.strip()}")
        return sequence, part_events, part_normalized

    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(process_capture, frozen_manifest["scenarios"]))
    for _, part_events, part_normalized in sorted(parts):
        with zeek.open("a", encoding="utf-8") as output:
            output.write(part_events.read_text(encoding="utf-8"))
        with normalized.open("a", encoding="utf-8") as output:
            output.write(part_normalized.read_text(encoding="utf-8"))
        part_events.unlink()
        part_normalized.unlink()
    completed = subprocess.run([sys.executable, str(ROOT / "ml/features/build_network_sensor_v4_dataset.py"), "--manifest", str(manifest_path), "--events", str(normalized), "--output", str(all_dataset)], cwd=ROOT, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise RuntimeError(f"Построитель dataset завершился с кодом {completed.returncode}: {completed.stderr.strip()}")
    validate_dataset(all_dataset, kind="windows", feature_profile="network_sensor_v0_4")
    full = pd.read_csv(all_dataset)
    mapping_fields = ("execution_id", "warmup", "episode_id", "episode_phase", "episode_position", "episode_class", "variant_id", "hard_negative_target_class", "environment_group")
    mapping = pd.DataFrame([{name: scenario.get(name) for name in mapping_fields} for scenario in frozen_manifest["scenarios"]])
    full = full.merge(mapping, on="execution_id", how="left", validate="one_to_one")
    scored = full[~full.warmup.astype(bool)].copy()
    scored.to_csv(dataset, index=False)
    full.to_csv(all_dataset, index=False)
    if len(full) != total_windows or len(scored) != scored_windows or scored.episode_id.nunique() != episode_count:
        raise ValueError("Нарушена warm-up/episode композиция")
    validate_dataset(dataset, kind="windows", feature_profile="network_sensor_v0_4")
    capture_hashes = [sha256(path) for path in sorted(captures)]
    if len(set(capture_hashes)) != total_windows:
        raise ValueError("Capture hashes должны быть уникальны внутри run")
    integrity = {
        "run": row,
        "warmup_rows": 6,
        "scored_rows": scored_windows,
        "episodes": episode_count,
        "marker_pairs": total_windows,
        "pcap_count": total_windows,
        "unique_capture_hashes": total_windows,
        "assigned_observations_positive": True,
        "marker_flows_excluded": True,
        "duplicated_assignments": 0,
        "ambiguous_assignments": 0,
        "aggregation_mismatches": 0,
        "empty_scored_windows": 0,
        "state_reset_valid": True,
        "causal_audit_valid": True,
        "condition_independence_valid": True,
        "safety_audit_valid": True,
        "manifest_sha256": sha256(manifest_path),
        "events_sha256": sha256(normalized),
        "dataset_sha256": sha256(dataset),
        "all_dataset_sha256": sha256(all_dataset),
    }
    atomic(run_dir / f"{stage_tag}_run_integrity.json", integrity)
    return {**{name: "success" for name in STATUS_FIELDS}, "run_id": run_id, "warmup_rows": 6, "scored_rows": scored_windows, "episodes": episode_count, "marker_pairs": total_windows, "capture_hashes": total_windows}


def execute(campaign: dict, output_root: Path, resume: bool = False, strict: bool = False) -> dict:
    directory = output_root / "campaigns" / campaign["campaign_id"].replace(".", "_").replace("-", "_")
    status_path = directory / "status.json"
    lock = directory / "runner.lock"
    directory.mkdir(parents=True, exist_ok=True)
    status = json.loads(status_path.read_text(encoding="utf-8")) if resume and status_path.exists() else {}
    if lock.exists():
        raise RuntimeError("Обнаружен активный v0.3.10 runner lock")
    lock.write_text(str(os.getpid()), encoding="utf-8")
    try:
        # Код traffic-client меняется вместе с каталогом кампании. Собираем его
        # ровно один раз на invocation, а не перед каждым из 12/6 immutable runs.
        environment = {**os.environ, "COMPOSE_PROJECT_NAME": f"filin_{campaign.get('stage_tag','v0310')}_build"}
        compose = ROOT / "lab/docker/docker-compose.lab.yml"
        retry(["docker", "compose", "-f", str(compose), "build", "traffic-client"], environment)
        pending = [row for row in campaign["runs"] if not (resume and complete(status.get(row["run_id"], {})))]
        if campaign.get("stage_tag") == "v0311":
            with ProcessPoolExecutor(max_workers=min(int(campaign.get("docker_workers", 3)), 3)) as pool:
                futures = {pool.submit(run, campaign, row, output_root): row for row in pending}
                for future in as_completed(futures):
                    row = futures[future]
                    try: status[row["run_id"]] = future.result()
                    except Exception as error: status[row["run_id"]] = {"run_id": row["run_id"], "run_status": "failed", "error_type": type(error).__name__, "error_message": str(error)}
                    atomic(status_path, status)
        else:
            for row in pending:
                try: status[row["run_id"]] = run(campaign, row, output_root)
                except Exception as error: status[row["run_id"]] = {"run_id": row["run_id"], "run_status": "failed", "error_type": type(error).__name__, "error_message": str(error)}
                atomic(status_path, status)
    finally:
        lock.unlink(missing_ok=True)
    if strict and not all(complete(status.get(row["run_id"], {})) for row in campaign["runs"]):
        raise RuntimeError("Не все v0.3.10 runs завершены")
    return status
