"""Параллельный resumable runner локальной Docker-кампании v0.3.13."""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from lab.campaigns.v0313_campaign import build_manifest


def _run_one(campaign, row, output_root):
    from lab.campaigns import v0310_runner
    v0310_runner.build_manifest = build_manifest
    return v0310_runner.run(campaign, row, output_root)


def execute(campaign: dict, output_root: Path, resume: bool = False, strict: bool = False) -> dict:
    from lab.campaigns import v0310_runner
    directory = output_root / "campaigns" / campaign["campaign_id"]
    status_path = directory / "status.json"
    lock = directory / "runner.lock"
    directory.mkdir(parents=True, exist_ok=True)
    status = json.loads(status_path.read_text(encoding="utf-8")) if resume and status_path.exists() else {}
    if lock.exists():
        raise RuntimeError("Обнаружен активный runner lock v0.3.13")
    lock.write_text(str(os.getpid()), encoding="utf-8")
    try:
        environment = {**os.environ, "COMPOSE_PROJECT_NAME": "filin_v0313_build"}
        compose = v0310_runner.ROOT / "lab/docker/docker-compose.lab.yml"
        v0310_runner.retry(["docker", "compose", "-f", str(compose), "build", "traffic-client"], environment)
        slot_root = directory / "zeek_worker_slots"
        slot_root.mkdir(exist_ok=True)
        for stale in slot_root.glob("slot_*"):
            if stale.is_dir():
                stale.rmdir()
        campaign = {**campaign, "_zeek_slot_root": str(slot_root.resolve())}
        pending = [row for row in campaign["runs"] if not (resume and v0310_runner.complete(status.get(row["run_id"], {})))]
        with ProcessPoolExecutor(max_workers=min(int(campaign.get("docker_workers", 3)), 3)) as pool:
            futures = {pool.submit(_run_one, campaign, row, output_root): row for row in pending}
            for future in as_completed(futures):
                row = futures[future]
                try:
                    status[row["run_id"]] = future.result()
                except Exception as error:
                    status[row["run_id"]] = {"run_id": row["run_id"], "run_status": "failed", "error_type": type(error).__name__, "error_message": str(error)}
                v0310_runner.atomic(status_path, status)
    finally:
        lock.unlink(missing_ok=True)
    if strict and not all(v0310_runner.complete(status.get(row["run_id"], {})) for row in campaign["runs"]):
        raise RuntimeError("Не все runs v0.3.13 завершены")
    return status
