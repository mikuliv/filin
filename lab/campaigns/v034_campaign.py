"""Deterministic planning for the isolated v0.3.4 train/validation campaigns."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ATTACKS = ("attack_port_scan", "attack_auth_failures", "attack_web_probe", "attack_low_rate_dos", "attack_beacon_simulation")


def stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_campaign(path: Path) -> dict[str, Any]:
    campaign = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    runs = campaign.get("runs", [])
    expected = 12 if campaign.get("campaign_id") == "filin-v0.3.4-training" else 6
    if len(runs) != expected or len({run.get("run_id") for run in runs}) != expected:
        raise ValueError("v0.3.4 campaign has an invalid run count")
    return campaign


def scenario_by_id(scenarios_dir: Path, identifier: str) -> dict[str, Any]:
    for path in scenarios_dir.rglob("*.yaml"):
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if value.get("scenario_id") == identifier:
            return value
    raise ValueError(f"Scenario {identifier} was not found")


def build_manifest(campaign: dict[str, Any], run: dict[str, Any], scenarios_dir: Path) -> dict[str, Any]:
    catalog = campaign["execution_catalog"]
    identifiers = [*catalog["benign"], *ATTACKS]
    if len(identifiers) != 21:
        raise ValueError("Each v0.3.4 run requires 16 benign and 5 attack executions")
    planned, rows = datetime.now(UTC).replace(microsecond=0), []
    for sequence, identifier in enumerate(identifiers, 1):
        raw = scenario_by_id(scenarios_dir, identifier)
        parameters = {"seed": run["random_seed"], "group": run["group"], "scenario_id": identifier, "variant": run.get("variant", run["group"])}
        duration = int(raw["duration_seconds"])
        rows.append({"run_sequence": sequence, "scenario_id": identifier, "type": raw["type"], "label": raw["expected_label"], "source_role": raw["source_role"], "target_role": raw["target_role"], "duration_seconds": duration, "planned_started_at": planned.isoformat().replace("+00:00", "Z"), "planned_finished_at": (planned + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z"), "actual_started_at": None, "actual_finished_at": None, "execution_status": "pending", "execution_id": f"{run['run_id']}:{sequence}:{identifier}", "scenario_variant_id": f"{identifier}:{stable_hash(parameters)[:12]}", "scenario_parameter_hash": stable_hash(parameters), "scenario_parameters": parameters, "environment_group": run["group"]})
        planned += timedelta(seconds=duration + 1)
    return {"manifest_version": "0.3.4", "run_id": run["run_id"], "campaign_id": campaign["campaign_id"], "campaign_version": "0.3.4", "campaign_role": campaign["role"], "campaign_run_index": run["run_index"], "campaign_seed": run["random_seed"], "execution_mode": "docker", "synthetic": False, "timezone": "UTC", "scenario_count": len(rows), "scenarios": rows}
