"""Детерминированный blind episode-план v0.3.13."""
from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

ATTACK_IDS = {"port_scan": "attack_port_scan", "auth_failures": "attack_auth_failures", "web_probe": "attack_web_probe", "low_rate_dos": "attack_low_rate_dos", "beacon": "attack_beacon_simulation"}
LENGTHS = (2, 3, 4, 5)
OFFSETS = (0, 3, 6, 8)


def stable(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def load(path: Path) -> dict:
    campaign = yaml.safe_load(path.read_text(encoding="utf-8"))
    runs = campaign.get("runs", [])
    if len(runs) != 10 or len({row["run_id"] for row in runs}) != 10 or len({row["random_seed"] for row in runs}) != 10:
        raise ValueError("Кампания v0.3.13 обязана содержать 10 уникальных runs и seeds")
    return campaign


def attack(root: Path, scenario_id: str) -> dict:
    for path in (root / "lab/scenarios/attacks").glob("*.yaml"):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if value.get("scenario_id") == scenario_id:
            return value
    raise KeyError(scenario_id)


def benign_schedule(root: Path) -> list[list[tuple[dict, str, int]]]:
    variants = yaml.safe_load((root / "ml/experiments/v0_3_13/benign_variants.yaml").read_text(encoding="utf-8"))["variants"]
    base = yaml.safe_load((root / "lab/scenarios/v0_3_11/validation_benign.yaml").read_text(encoding="utf-8"))["scenarios"][:10]
    counts = [[3, 2, 2, 3] if run % 2 == 0 else [2, 3, 3, 2] for run in range(10)]
    cursors = [0, 0, 0, 0]
    result = [[] for _ in range(10)]
    for run in range(10):
        for length_index, length in enumerate(LENGTHS):
            for _ in range(counts[run][length_index]):
                variant_index = (cursors[length_index] + OFFSETS[length_index]) % 25
                result[run].append((base[variant_index % len(base)], variants[variant_index], length))
                cursors[length_index] += 1
        if len({variant for _, variant, _ in result[run]}) != 10 or sum(length for _, _, length in result[run]) != 35:
            raise RuntimeError("Нарушен benign Latin-square schedule")
    flattened = [(variant, length) for run in result for _, variant, length in run]
    if any(sum(v == variant for v, _ in flattened) != 4 for variant in variants):
        raise RuntimeError("Каждый benign variant обязан иметь четыре эпизода")
    if any(sorted(length for v, length in flattened if v == variant) != list(LENGTHS) for variant in variants):
        raise RuntimeError("Benign episode lengths не сбалансированы")
    return result


def build_manifest(root: Path, campaign: dict, run: dict) -> dict:
    run_index = int(run["run_index"])
    benign = benign_schedule(root)[run_index - 1]
    episodes = [(item, f"{run['run_id']}:benign:{index + 1}", "benign", variant, length) for index, (item, variant, length) in enumerate(benign)]
    for class_index, (label, scenario_id) in enumerate(ATTACK_IDS.items()):
        pair = (2, 5) if (run_index + class_index) % 2 == 0 else (3, 4)
        item = attack(root, scenario_id)
        for ordinal, length in enumerate(pair, 1):
            episodes.append((item, f"{run['run_id']}:attack:{label}:{ordinal}", label, f"{scenario_id}:v0313:{ordinal}", length))
    random.Random(int(run["random_seed"])).shuffle(episodes)
    warm = benign[0][0]
    expanded = [(warm, None, "warmup", "warmup", 0, position) for position in range(1, 7)]
    for item, episode_id, label, variant, length in episodes:
        expanded.extend((item, episode_id, label, variant, length, position) for position in range(1, length + 1))
    if len(expanded) != 76:
        raise RuntimeError("Run v0.3.13 обязан содержать 76 окон")
    planned = datetime(2026, 7, 20, tzinfo=UTC) + timedelta(days=run_index, seconds=int(run["random_seed"]))
    rows = []
    for sequence, (item, episode_id, label, variant, length, position) in enumerate(expanded, 1):
        environment = {
            "background_profile": f"{run['group']}:background:{run['random_seed'] % 7}",
            "timing_profile": f"{run['group']}:jitter:{(sequence + run_index) % 5}",
            "topology_profile": f"local-services:{3 + run_index % 4}",
            "resource_profile": f"bounded:{(run_index % 3) + 1}",
            "service_composition": ["target-web", "target-api", "control-api", "target-ssh-sim"][: 2 + run_index % 3],
        }
        parameters = {"generator_version": "v0313-safe-local-v1", "environmental_group": run["group"], "episode_length": length, "schedule_seed": int(run["random_seed"]) + sequence, **environment}
        duration = int(item.get("duration_seconds", 20))
        warmup = episode_id is None
        rows.append({
            "run_sequence": sequence, "scenario_id": item["scenario_id"], "type": item["type"], "label": item["expected_label"], "source_role": item["source_role"], "target_role": item["target_role"], "duration_seconds": duration,
            "planned_started_at": planned.isoformat().replace("+00:00", "Z"), "planned_finished_at": (planned + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z"), "actual_started_at": None, "actual_finished_at": None, "execution_status": "pending",
            "execution_id": f"{run['run_id']}:{sequence}:{item['scenario_id']}", "scenario_variant_id": f"{variant}:{stable(parameters)[:12]}", "scenario_parameter_hash": stable(parameters), "scenario_fingerprint": stable(parameters), "scenario_parameters": parameters,
            "environment_group": run["group"], "warmup": warmup, "episode_id": episode_id, "episode_phase": "warmup" if warmup else f"phase_{position}", "episode_position": 0 if warmup else position, "episode_length": 0 if warmup else length, "episode_class": label, "variant_id": variant, "hard_negative_target_class": item.get("hard_negative_target_class"),
        })
        planned += timedelta(seconds=duration + (181 if episode_id is not None and position == length else 1))
    return {
        "manifest_version": "0.3.13", "run_id": run["run_id"], "campaign_id": campaign["campaign_id"], "campaign_version": "0.3.13", "campaign_role": campaign["role"], "campaign_run_index": run_index, "campaign_seed": run["random_seed"], "execution_mode": "docker", "synthetic": False, "timezone": "UTC", "capture_dns": True,
        "network_policy": {"scope": "internal_docker_only", "external_dns_allowed": False, "host_network_allowed": False, "allowed_dns_names": ["target-web", "target-api", "control-api", "target-ssh-sim", "filin-missing-service"]}, "scenario_count": 76, "environment_group": run["group"], "scenarios": rows,
    }
