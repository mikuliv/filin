from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from collectors.shadow.fault_registry import REGISTRY


ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_2"
RUNTIME = ROOT / "runtime/v0_3_15_2"
GROUPS = [
    "prospective_baseline_endurance",
    "prospective_burst_jitter",
    "prospective_overload_backpressure",
    "prospective_ack_transport_fault",
    "prospective_crash_resume",
    "prospective_clock_integrity",
]
SEEDS = [19101, 19102, 19201, 19202, 19301, 19302, 19401, 19402, 19501, 19502, 19601, 19602]
ATTACKS = ["auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"]


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_yaml(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def sessions() -> list[dict]:
    return [
        {
            "session_id": f"{group}_{number:03d}",
            "group": group,
            "seed": SEEDS[index],
            "session_index": index,
            "capture_windows": 200,
            "warmup_windows": 10,
            "scored_windows": 190,
        }
        for index, (group, number) in enumerate((group, number) for group in GROUPS for number in (1, 2))
    ]


def episode_schedule(rows: list[dict]) -> list[dict]:
    result = []
    for session in rows:
        index = session["session_index"]
        benign_variants = range(index * 5, index * 5 + 5) if index < 6 else [((index - 7) % 6) * 5 + offset for offset in range(5)]
        for position, variant in enumerate(benign_variants):
            length = 2 + ((index * 5 + position) % 4)
            result.append({
                "episode_id": f"{session['session_id']}:benign:{position + 1}",
                "session_id": session["session_id"], "session_group": session["group"],
                "kind": "benign", "class": "benign", "length": length,
                "start_scored_window": position * 18, "benign_variant": f"prospective_benign_{variant + 1:02d}",
                "generation_nonce": digest([session["seed"], "benign", position])[:16],
            })
        for position, attack in enumerate(ATTACKS):
            length = 2 + (index % 4)
            result.append({
                "episode_id": f"{session['session_id']}:attack:{attack}",
                "session_id": session["session_id"], "session_group": session["group"],
                "kind": "attack", "class": attack, "length": length,
                "start_scored_window": 95 + position * 18, "benign_variant": None,
                "generation_nonce": digest([session["seed"], attack, position])[:16],
            })
    return result


def fault_schedule(rows: list[dict]) -> list[dict]:
    targets = rows[4:]
    result = []
    for index, name in enumerate(REGISTRY):
        session = targets[index % len(targets)]
        result.append({
            "fault_id": f"fault-{index + 1:02d}", "fault_name": name,
            "session_id": session["session_id"], "causal_window": 12 + (index // len(targets)) * 31 + (index % len(targets)) * 2,
            "runtime_boundary": "integrated_exporter", "expected_effect": "отличающийся от healthy path наблюдаемый результат",
            "expected_recovery": "bounded recovery и итоговая reconciliation", "maximum_attempts": 4,
            "timeout_seconds": 30, "affected_event_class": "diagnostic_fixture",
            "source_sink_equality_expected": name not in {"schema_rejection"}, "corpus": "adversarial" if name in {"schema_rejection", "malformed_ack", "unknown_ack", "event_corruption"} else "canonical",
        })
    return result


def label_vault(rows: list[dict], episodes: list[dict]) -> dict:
    by_session = {}
    for episode in episodes:
        by_session.setdefault(episode["session_id"], []).append(episode)
    records = []
    for session in rows:
        for scored in range(190):
            match = next((item for item in by_session[session["session_id"]] if item["start_scored_window"] <= scored < item["start_scored_window"] + item["length"]), None)
            records.append({
                "session_id": session["session_id"], "scored_window_index": scored,
                "true_class": match["class"] if match else "benign",
                "episode_id": match["episode_id"] if match else None,
                "episode_kind": match["kind"] if match else None,
                "episode_length": match["length"] if match else None,
                "episode_position": scored - match["start_scored_window"] + 1 if match else None,
                "benign_variant": match["benign_variant"] if match else None,
            })
    return {"schema_version": "v03152_label_vault_v1", "sealed": True, "unlocked": False, "record_count": len(records), "records": records}


def main() -> int:
    CFG.mkdir(parents=True, exist_ok=True); RUNTIME.mkdir(parents=True, exist_ok=True)
    session_rows = sessions(); episodes = episode_schedule(session_rows); faults = fault_schedule(session_rows); vault = label_vault(session_rows, episodes)
    assert len(session_rows) == 12 and len(episodes) == 120 and len(faults) == 35 and len(vault["records"]) == 2280
    assert len(set(SEEDS)) == 12
    assert all(sum(item["class"] == attack for item in episodes) == 12 for attack in ATTACKS)
    assert all(sum(item["length"] == length and item["kind"] == kind for item in episodes) == 15 for length in range(2, 6) for kind in ("benign", "attack"))
    variants = {name: [] for name in [f"prospective_benign_{value:02d}" for value in range(1, 31)]}
    for item in episodes:
        if item["benign_variant"]: variants[item["benign_variant"]].append(item)
    assert all(len(items) == 2 and items[0]["session_group"] != items[1]["session_group"] for items in variants.values())
    campaign = {
        "schema_version": "v03152_campaign_v1", "campaign_id": "filin_v0_3_15_2_prospective_integrated_runtime_trial",
        "protocol_revision": 2, "sequential_sessions": True, "active_session_limit": 1,
        "session_count": 12, "capture_window_count": 2400, "warmup_window_count": 120, "scored_window_count": 2280,
        "episode_count": 120, "benign_episode_count": 60, "attack_episode_count": 60,
        "profile": {"name": "C", "workers": 2, "batch_size": 50},
        "sessions": session_rows,
    }
    write_yaml(CFG / "campaign.yaml", campaign)
    write_yaml(CFG / "session_manifest.yaml", {"schema_version": "v03152_sessions_v1", "sessions": session_rows})
    write_yaml(CFG / "episode_schedule.yaml", {"schema_version": "v03152_episodes_v1", "episodes": episodes})
    write_yaml(CFG / "fault_schedule.yaml", {"schema_version": "v03152_faults_v1", "faults": faults})
    write_json(RUNTIME / "label_vault.json", vault)
    hashes = {name: file_digest(CFG / name) for name in ("campaign.yaml", "session_manifest.yaml", "episode_schedule.yaml", "fault_schedule.yaml")}
    lock = {
        "schema_version": "v03152_campaign_lock_v1", "protocol_sha256": file_digest(ROOT / "ml/protocols/v0_3_15_2_protocol.yaml"),
        **{name.removesuffix(".yaml") + "_sha256": value for name, value in hashes.items()},
        "label_vault_sha256": file_digest(RUNTIME / "label_vault.json"), "scenario_schedule_sha256": hashes["fault_schedule.yaml"],
        "campaign_sha256": digest({**hashes, "label_vault_sha256": file_digest(RUNTIME / "label_vault.json")}),
        "frozen_before_capture": True, "seed_reuse_count": 0,
    }
    write_json(CFG / "campaign_lock.json", lock)
    print(json.dumps(lock, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
