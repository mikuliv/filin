"""Planning helpers for the v0.3.3 external environment campaign.

The helpers deliberately keep environment metadata outside model features.  They
build a deterministic 17-execution manifest which the Docker runner can resume
without changing an already successful run.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml


ATTACK_SCENARIOS = (
    "attack_port_scan",
    "attack_auth_failures",
    "attack_web_probe",
    "attack_low_rate_dos",
    "attack_beacon_simulation",
)


def stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_campaign(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("campaign_id") != "filin-v0.3.3-environment":
        raise ValueError("Ожидалась кампания filin-v0.3.3-environment.")
    runs = data.get("runs") or []
    if len(runs) != 12 or len({item.get("run_id") for item in runs}) != 12:
        raise ValueError("Кампания v0.3.3 должна содержать 12 уникальных runs.")
    return data


def scenario_path(scenarios_dir: Path, scenario_id: str) -> Path:
    for path in scenarios_dir.rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("scenario_id") == scenario_id:
            return path
    raise ValueError(f"Не найден YAML сценария {scenario_id}.")


def build_run_manifest(campaign: dict[str, Any], run: dict[str, Any], scenarios_dir: Path) -> dict[str, Any]:
    catalog = campaign.get("execution_catalog") or {}
    scenario_ids = list(catalog.get("benign") or []) + list(catalog.get("attacks") or [])
    if len(scenario_ids) != 17 or tuple(scenario_ids[-5:]) != ATTACK_SCENARIOS:
        raise ValueError("v0.3.3 требует 12 benign и 5 неизменных attack executions.")
    entries: list[dict[str, Any]] = []
    planned = datetime.now(UTC).replace(microsecond=0)
    for sequence, scenario_id in enumerate(scenario_ids, start=1):
        raw = yaml.safe_load(scenario_path(scenarios_dir, scenario_id).read_text(encoding="utf-8"))
        parameters = {"seed": run["random_seed"], "group": run["group"], "scenario_id": scenario_id}
        parameter_hash = stable_hash(parameters)
        duration = int(raw["duration_seconds"])
        entries.append({
            "run_sequence": sequence,
            "scenario_id": scenario_id,
            "type": raw["type"],
            "label": raw["expected_label"],
            "source_role": raw["source_role"],
            "target_role": raw["target_role"],
            "duration_seconds": duration,
            "planned_started_at": planned.isoformat().replace("+00:00", "Z"),
            "planned_finished_at": (planned + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z"),
            "actual_started_at": None,
            "actual_finished_at": None,
            "execution_status": "pending",
            "execution_id": f"{run['run_id']}:{sequence}:{scenario_id}",
            "scenario_variant_id": f"{scenario_id}:{parameter_hash[:12]}",
            "scenario_parameter_hash": parameter_hash,
            "scenario_parameters": parameters,
            "environment_group": run["group"],
        })
        planned += timedelta(seconds=duration + 1)
    return {
        "manifest_version": "0.3.3",
        "run_id": run["run_id"],
        "campaign_id": campaign["campaign_id"],
        "campaign_version": campaign["campaign_version"],
        "campaign_role": run["role"],
        "campaign_run_index": run["run_index"],
        "campaign_seed": run["random_seed"],
        "environment_group": run["group"],
        "execution_mode": "docker",
        "synthetic": False,
        "timezone": "UTC",
        "scenario_count": len(entries),
        "scenarios": entries,
    }


def run_is_complete(status: dict[str, Any]) -> bool:
    required = {
        "run_status", "capture_audit_status", "correlation_audit_status",
        "aggregation_consistency_status", "sensor_validator_status", "dataset_status",
    }
    return required <= set(status) and all(status[name] == "success" for name in required)

