from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_4"
RUNTIME = ROOT / "runtime/v0_3_15_4"
PROTOCOL = ROOT / "ml/protocols/v0_3_15_4_protocol.yaml"
GROUPS = ["scenario_semantics", "feature_provenance", "subtype_boundary", "conformal_behavior", "benign_hard_negatives"]
ATTACKS = ["auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def build_sessions() -> list[dict]:
    rows = []
    for group_index, group in enumerate(GROUPS):
        for suffix in range(1, 6):
            split = "training" if suffix <= 3 else "calibration" if suffix == 4 else "internal_audit"
            rows.append({
                "session_id": f"dev2_{group}_{suffix:03d}", "group": group,
                "seed": 21101 + group_index * 100 + suffix - 1,
                "session_index": len(rows), "split": split,
                "capture_count": 200, "warmup_count": 10, "scored_count": 190,
            })
    return rows


def build_episodes(sessions: list[dict]) -> list[dict]:
    result: list[dict] = []
    attack_seen = Counter()
    benign_seen = Counter()
    by_session_benign: dict[int, list[int]] = defaultdict(list)
    for variant in range(50):
        by_session_benign[variant % 25].append(variant)
        by_session_benign[(variant + 6) % 25].append(variant)
    assert all(len(values) == 4 for values in by_session_benign.values())
    starts = [12, 34, 56, 78, 100, 122, 144, 166]
    for session in sessions:
        index = session["session_index"]
        group_index, suffix_index = index // 5, index % 5
        omitted = (group_index + suffix_index) % 5
        attacks = [attack for attack_index, attack in enumerate(ATTACKS) if attack_index != omitted]
        variants = sorted(by_session_benign[index])
        specifications = [("attack", value) for value in attacks] + [("benign", value) for value in variants]
        for slot, (kind, value) in enumerate(specifications):
            if kind == "attack":
                occurrence = attack_seen[value]; attack_seen[value] += 1
                label = value; length = 2 + occurrence % 4; variant_name = None
            else:
                occurrence = benign_seen[value]; benign_seen[value] += 1
                label = "benign"; length = 2 + ((sum(benign_seen.values()) - 1) % 4)
                variant_name = f"hard_negative_{value + 1:02d}"
            result.append({
                "episode_id": f"v03154:{session['session_id']}:{slot + 1:02d}",
                "session_id": session["session_id"], "session_group": session["group"],
                "split": session["split"], "kind": kind, "class": label,
                "start_scored_window": starts[slot], "length": length,
                "benign_variant": variant_name,
                "generation_nonce": digest([session["seed"], slot, value, occurrence])[:20],
            })
    return result


def build_label_vault(sessions: list[dict], episodes: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for episode in episodes:
        grouped[episode["session_id"]].append(episode)
    records = []
    for session in sessions:
        for scored in range(190):
            episode = next((row for row in grouped[session["session_id"]] if row["start_scored_window"] <= scored < row["start_scored_window"] + row["length"]), None)
            records.append({
                "session_id": session["session_id"], "split": session["split"],
                "scored_window_index": scored, "true_class": episode["class"] if episode else "benign",
                "episode_id": episode["episode_id"] if episode else None,
                "episode_kind": episode["kind"] if episode else None,
                "episode_position": scored - episode["start_scored_window"] + 1 if episode else None,
                "benign_variant": episode["benign_variant"] if episode else None,
            })
    return {"schema_version": "v03154_label_vault_v1", "sealed": True, "record_count": len(records), "records": records}


def validate(sessions: list[dict], episodes: list[dict], vault: dict) -> None:
    assert len(sessions) == 25 and len({x["seed"] for x in sessions}) == 25
    assert Counter(x["split"] for x in sessions) == {"training": 15, "calibration": 5, "internal_audit": 5}
    assert len(episodes) == 200 and Counter(x["kind"] for x in episodes) == {"attack": 100, "benign": 100}
    assert all(sum(x["class"] == attack for x in episodes) == 20 for attack in ATTACKS)
    for attack in ATTACKS:
        assert Counter(x["length"] for x in episodes if x["class"] == attack) == {2: 5, 3: 5, 4: 5, 5: 5}
    assert Counter(x["length"] for x in episodes if x["kind"] == "benign") == {2: 25, 3: 25, 4: 25, 5: 25}
    variants = defaultdict(list)
    for row in episodes:
        if row["benign_variant"]:
            variants[row["benign_variant"]].append(row)
    assert len(variants) == 50
    assert all(len(rows) == 2 and rows[0]["session_id"] != rows[1]["session_id"] and rows[0]["session_group"] != rows[1]["session_group"] and rows[0]["generation_nonce"] != rows[1]["generation_nonce"] for rows in variants.values())
    assert len(vault["records"]) == 4750


def main() -> int:
    sessions = build_sessions(); episodes = build_episodes(sessions); vault = build_label_vault(sessions, episodes)
    validate(sessions, episodes, vault)
    campaign = {
        "schema_version": "v03154_campaign_v1", "campaign_id": "filin_v0_3_15_4_controlled_redevelopment",
        "protocol_revision": 2, "frozen_before_first_capture": True,
        "session_count": 25, "capture_count": 5000, "warmup_count": 250, "scored_count": 4750,
        "episode_count": 200, "attack_episode_count": 100, "benign_episode_count": 100,
        "containerized_zeek": "7.0.5", "fallback_allowed": False, "sessions": sessions,
    }
    write_yaml(CFG / "campaign.yaml", campaign)
    write_yaml(CFG / "session_manifest.yaml", {"schema_version": "v03154_sessions_v1", "sessions": sessions})
    write_yaml(CFG / "episode_schedule.yaml", {"schema_version": "v03154_episodes_v1", "episodes": episodes})
    write_yaml(CFG / "split_manifest.yaml", {"schema_version": "v03154_split_v1", "unit": "whole_session_id", "assignments": [{"session_id": x["session_id"], "split": x["split"]} for x in sessions]})
    write_json(RUNTIME / "label_vault.json", vault)
    names = ["campaign.yaml", "session_manifest.yaml", "episode_schedule.yaml", "split_manifest.yaml"]
    hashes = {name: file_digest(CFG / name) for name in names}
    lock = {
        "schema_version": "v03154_campaign_lock_v1", "protocol_sha256": file_digest(PROTOCOL),
        **{name.replace(".yaml", "_sha256"): value for name, value in hashes.items()},
        "label_vault_sha256": file_digest(RUNTIME / "label_vault.json"),
        "campaign_commitment_sha256": digest([hashes, file_digest(RUNTIME / "label_vault.json")]),
        "frozen_before_first_capture": True, "first_capture_exists": False,
        "audit_labels_sealed": True, "search_space_frozen": True,
    }
    write_json(CFG / "campaign_lock.json", lock)
    print(json.dumps(lock, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
