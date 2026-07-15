"""Детерминированное трёхоконное episode-планирование кампаний v0.3.10."""
from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml


ATTACK_IDS = {
    "port_scan": "attack_port_scan",
    "auth_failures": "attack_auth_failures",
    "web_probe": "attack_web_probe",
    "low_rate_dos": "attack_low_rate_dos",
    "beacon_simulation": "attack_beacon_simulation",
}


def stable(value) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load(path: Path) -> dict:
    campaign = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = 12 if campaign["role"] == "minimal_promotion_training" else 6
    if len(campaign["runs"]) != expected or len({row["run_id"] for row in campaign["runs"]}) != expected:
        raise ValueError("Некорректное число или повтор run_id v0.3.10")
    return campaign


def catalog(root: Path, campaign: dict) -> list[dict]:
    return yaml.safe_load((root / campaign["catalog"]).read_text(encoding="utf-8"))["scenarios"]


def selected_scenarios(items: list[dict], run_index: int) -> list[dict]:
    selected = [item for index, item in enumerate(items) if (index + run_index - 1) % 2 == 0]
    if len(selected) != 8:
        raise ValueError("Balance schedule обязан выбрать 9 benign scenarios")
    return selected


def attack_scenario(root: Path, scenario_id: str) -> dict:
    for path in (root / "lab/scenarios/attacks").glob("*.yaml"):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if value.get("scenario_id") == scenario_id:
            return value
    raise KeyError(scenario_id)


def build_manifest(root: Path, campaign: dict, run: dict) -> dict:
    chosen = selected_scenarios(catalog(root, campaign), int(run["run_index"]))
    rng = random.Random(int(run["random_seed"]))
    warmups = [(chosen[index % len(chosen)], True, None, "warmup", "warmup") for index in range(6)]
    episodes = [(item, False, f"{run['run_id']}:benign:{index + 1}", "benign", item["scenario_id"]) for index, item in enumerate(chosen)]
    for label, scenario_id in ATTACK_IDS.items():
        item = attack_scenario(root, scenario_id)
        episodes.append((item, False, f"{run['run_id']}:attack:{label}:strong", label, f"{scenario_id}:strong_onset"))
        episodes.append((item, False, f"{run['run_id']}:attack:{label}:gradual", label, f"{scenario_id}:gradual_onset"))
    rng.shuffle(episodes)
    executions = list(warmups)
    expanded = []
    for item, warmup, episode_id, label, variant in episodes:
        expanded.extend((item, warmup, episode_id, label, variant, phase) for phase in ("phase_1", "phase_2", "phase_3"))
    executions.extend(expanded)
    planned = datetime.now(UTC).replace(microsecond=0)
    rows = []
    for sequence, values in enumerate(executions, 1):
        if len(values) == 5:
            item, warmup, episode_id, label, variant = values
            phase = "warmup"
        else:
            item, warmup, episode_id, label, variant, phase = values
        duration = int(item.get("duration_seconds", 20))
        parameters = {
            "run_seed": int(run["random_seed"]),
            "scenario_seed": int(run["random_seed"]) + sequence,
            "group": run["group"],
            "warmup": warmup,
            "episode_id": episode_id,
            "episode_phase": phase,
            "parameter_ordinal": sequence,
        }
        rows.append({
            "run_sequence": sequence,
            "scenario_id": item["scenario_id"],
            "type": item["type"],
            "label": item["expected_label"],
            "source_role": item["source_role"],
            "target_role": item["target_role"],
            "duration_seconds": duration,
            "planned_started_at": planned.isoformat().replace("+00:00", "Z"),
            "planned_finished_at": (planned + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z"),
            "actual_started_at": None,
            "actual_finished_at": None,
            "execution_status": "pending",
            "execution_id": f"{run['run_id']}:{sequence}:{item['scenario_id']}",
            "scenario_variant_id": f"{item['scenario_id']}:{stable(parameters)[:12]}",
            "scenario_parameter_hash": stable(parameters),
            "scenario_parameters": parameters,
            "environment_group": run["group"],
            "warmup": warmup,
            "episode_id": episode_id,
            "episode_phase": phase,
            "episode_position": 0 if warmup else int(phase[-1]),
            "episode_class": label,
            "variant_id": item["scenario_id"],
            "hard_negative_target_class": item.get("hard_negative_target_class"),
        })
        planned += timedelta(seconds=duration + (181 if phase == "phase_3" else 1))
    if len(rows) != 60:
        raise ValueError("Run v0.3.10 обязан содержать 60 execution-окон")
    return {
        "manifest_version": "0.3.10",
        "run_id": run["run_id"],
        "campaign_id": campaign["campaign_id"],
        "campaign_version": "0.3.10",
        "campaign_role": campaign["role"],
        "campaign_run_index": run["run_index"],
        "campaign_seed": run["random_seed"],
        "execution_mode": "docker",
        "synthetic": False,
        "timezone": "UTC",
        "capture_dns": True,
        "network_policy": {
            "scope": "internal_docker_only",
            "external_dns_allowed": False,
            "allowed_dns_names": ["target-web", "target-api", "control-api", "target-ssh-sim", "filin-missing-service"],
        },
        "scenario_count": len(rows),
        "scenarios": rows,
    }
