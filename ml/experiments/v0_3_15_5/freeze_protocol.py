from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_5"
REPORT = ROOT / "ml/reports/v0_3_15_5"
RUNTIME = ROOT / "runtime/v0_3_15_5"
PROTOCOL = ROOT / "ml/protocols/v0_3_15_5_protocol.yaml"
GROUPS = ["balanced", "auth_generalization", "web_probe_generalization", "background_shift", "runtime_resilience"]
ATTACKS = ["auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"]
SEED_BASES = [22101, 22201, 22301, 22401, 22501]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")


def sessions() -> list[dict]:
    rows = []
    for gi, group in enumerate(GROUPS):
        for suffix in range(1, 5):
            rows.append({"session_id": f"holdout_{group}_{suffix:03d}", "session_group": group,
                         "session_index": len(rows), "seed": SEED_BASES[gi] + suffix - 1,
                         "capture_count": 200, "warmup_count": 10, "scored_count": 190})
    return rows


def episodes(session_rows: list[dict]) -> list[dict]:
    starts = [10, 28, 46, 64, 82, 100, 118, 136, 154, 172]
    benign_by_session: dict[int, list[int]] = defaultdict(list)
    for variant in range(50):
        benign_by_session[variant % 20].append(variant)
        benign_by_session[(variant + 10) % 20].append(variant)
    result = []
    benign_occurrence = Counter()
    benign_length_counter = 0
    for session in session_rows:
        si = session["session_index"]
        entries = [("attack", ATTACKS[(slot + si) % 5]) for slot in range(5)]
        entries += [("benign", variant) for variant in sorted(benign_by_session[si])]
        assert len(entries) == 10
        for slot, (kind, value) in enumerate(entries):
            if kind == "attack":
                attack = str(value)
                occurrence = si
                length = 2 + (si % 4)
                variant_id = f"{attack}_holdout_{si + 1:02d}"
                parameter_vector = {
                    "variant_nonce": digest(["attack", attack, session["seed"], slot])[:16],
                    "attempts_or_flows": 4 + ((si + slot) % 5), "spacing_ms": 11 + si * 3 + slot,
                    "payload_size": 72 + si * 7 + slot * 3, "response_order": (si + slot) % 3,
                    "timeout_mode": (si + slot) % 2, "background_level": 1 + (si % 4),
                }
                benign_variant = None
            else:
                attack = "benign"
                variant = int(value)
                occurrence = benign_occurrence[variant]; benign_occurrence[variant] += 1
                length = 2 + (benign_length_counter % 4); benign_length_counter += 1
                variant_id = f"benign_holdout_{variant + 1:02d}"
                parameter_vector = {"variant_nonce": digest(["benign", variant, session["seed"], occurrence])[:16],
                                    "workflow": variant % 12, "pace_ms": 19 + variant + occurrence * 7,
                                    "response_mode": (variant + occurrence) % 5, "background_level": 1 + (variant % 4)}
                benign_variant = variant_id
            result.append({"episode_id": f"v03155:{session['session_id']}:{slot + 1:02d}",
                           "session_id": session["session_id"], "session_group": session["session_group"],
                           "slot": slot + 1, "start_scored_window": starts[slot], "length": length,
                           "kind": kind, "class": attack, "variant_id": variant_id,
                           "benign_variant_id": benign_variant, "activity_slot": slot + 1,
                           "parameter_vector": parameter_vector,
                           "parameter_vector_sha256": digest(parameter_vector)})
    return result


def validate(session_rows: list[dict], episode_rows: list[dict]) -> None:
    assert len(session_rows) == 20 and len({r["session_id"] for r in session_rows}) == 20
    assert len({r["seed"] for r in session_rows}) == 20
    assert not any(21101 <= r["seed"] <= 21505 for r in session_rows)
    assert Counter(r["session_group"] for r in session_rows) == {g: 4 for g in GROUPS}
    assert Counter(r["kind"] for r in episode_rows) == {"attack": 100, "benign": 100}
    for attack in ATTACKS:
        rows = [r for r in episode_rows if r["class"] == attack]
        assert len(rows) == 20 and Counter(r["length"] for r in rows) == {2: 5, 3: 5, 4: 5, 5: 5}
        assert len({r["parameter_vector_sha256"] for r in rows}) == 20
    assert Counter(r["length"] for r in episode_rows if r["kind"] == "benign") == {2: 25, 3: 25, 4: 25, 5: 25}
    grouped = defaultdict(list)
    for row in episode_rows:
        if row["benign_variant_id"]:
            grouped[row["benign_variant_id"]].append(row)
    assert len(grouped) == 50
    assert all(len(v) == 2 and v[0]["session_id"] != v[1]["session_id"] and v[0]["session_group"] != v[1]["session_group"] for v in grouped.values())
    assert len({r["episode_id"] for r in episode_rows}) == 200


def main() -> int:
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        allowed = {"docs/experiments/v0_3_15_5.md", "ml/protocols/v0_3_15_5_protocol.yaml",
                   "ml/experiments/v0_3_15_5/__init__.py", "ml/experiments/v0_3_15_5/freeze_protocol.py"}
        changed = {line[3:].replace("\\", "/") for line in subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines()}
        unexpected = {path for path in changed if path not in allowed and not path.startswith("ml/experiments/v0_3_15_5/")}
        if unexpected:
            raise RuntimeError(f"unexpected_dirty_paths:{sorted(unexpected)}")
    ss = sessions(); ee = episodes(ss); validate(ss, ee)
    campaign = {"schema_version": "v03155_campaign_v1", "campaign_id": "filin_v0_3_15_5_independent_holdout",
                "frozen_before_first_capture": True, "protocol_revision": 1, "session_count": 20,
                "capture_count": 4000, "warmup_count": 200, "scored_count": 3800,
                "episode_count": 200, "attack_episode_count": 100, "benign_episode_count": 100,
                "sessions": ss}
    write_yaml(CFG / "campaign.yaml", campaign)
    write_yaml(CFG / "session_manifest.yaml", {"schema_version": "v03155_sessions_v1", "sessions": ss})
    write_yaml(CFG / "episode_schedule.yaml", {"schema_version": "v03155_episode_schedule_v1", "episodes": ee})
    attack_variants = [{k: r[k] for k in ("variant_id", "class", "parameter_vector", "parameter_vector_sha256")} for r in ee if r["kind"] == "attack"]
    benign_variants = [{k: r[k] for k in ("variant_id", "session_id", "session_group", "parameter_vector", "parameter_vector_sha256")} for r in ee if r["kind"] == "benign"]
    write_yaml(CFG / "scenario_variant_manifest.yaml", {"schema_version": "v03155_attack_variants_v1", "variants": attack_variants})
    write_yaml(CFG / "benign_variant_manifest.yaml", {"schema_version": "v03155_benign_variants_v1", "assignments": benign_variants})
    vault_records = []
    by_session = defaultdict(list)
    for row in ee: by_session[row["session_id"]].append(row)
    for session in ss:
        for index in range(190):
            episode = next((r for r in by_session[session["session_id"]] if r["start_scored_window"] <= index < r["start_scored_window"] + r["length"]), None)
            vault_records.append({"session_id": session["session_id"], "scored_window_index": index,
                                  "true_class": episode["class"] if episode else "benign",
                                  "episode_id": episode["episode_id"] if episode else None,
                                  "episode_position": index - episode["start_scored_window"] + 1 if episode else None,
                                  "episode_kind": episode["kind"] if episode else None,
                                  "variant_id": episode["variant_id"] if episode else None,
                                  "activity_slot": episode["activity_slot"] if episode else 0})
    write_json(RUNTIME / "label_vault.json", {"schema_version": "v03155_label_vault_v1", "sealed": True, "records": vault_records})
    write_json(REPORT / "baseline_comparator_eligibility_report.json", {
        "schema_version": "v03155_baseline_eligibility_v1", "baseline_candidate_id": "v0311:19176acb401be2d4",
        "baseline_feature_contract": "network_sensor_v0_5_contextual_control", "uses_label": False,
        "uses_scenario_name": False, "uses_generator_profile": True, "uses_hidden_state": True,
        "uses_future_data": False, "uses_noncausal_order": False, "exact_historical_path_available": True,
        "baseline_comparator_eligible": False,
        "limitations": ["Historical PCAP extractor selects a profile from destination ports, flow count and packet count.", "A v2 reinterpretation may not be substituted under the historical candidate ID."],
        "evidence": ["collectors/shadow_trial/window_processor.py:112", "collectors/shadow_trial/window_processor.py:128-134"]})
    pair = {"schema_version": "v03155_candidate_pair_lock_v1", "locked_before_first_capture": True,
            "candidate": yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))["candidate"],
            "baseline": yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))["baseline"],
            "candidate_feature_contract_sha256": sha(ROOT / "ml/experiments/v0_3_15_4/feature_contract_v2.yaml"),
            "candidate_state_policy_sha256": "3b1acd1a066b278a75c2edc5152c64ee2dd962fee21bd7b43acffb567e4a700c",
            "candidate_event_contract_sha256": "cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe",
            "execution_order": ["candidate", "baseline_if_eligible"], "baseline_inference_allowed": False}
    write_json(REPORT / "candidate_pair_lock.json", pair)
    historical_paths = []
    for stage in ["v0_3_11", "v0_3_12", "v0_3_12_1", "v0_3_12_2", "v0_3_13", "v0_3_14", "v0_3_15", "v0_3_15_1", "v0_3_15_2", "v0_3_15_3", "v0_3_15_4"]:
        for base in (ROOT / "ml/protocols", ROOT / "ml/experiments", ROOT / "ml/reports"):
            for path in sorted(base.glob(f"**/*{stage}*")):
                if path.is_file(): historical_paths.append(path)
    historical = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(historical_paths))}
    write_json(RUNTIME / "historical_hashes_before.json", historical)
    independence = {"schema_version": "v03155_independence_manifest_v1", "frozen_before_first_capture": True,
                    "historical_scopes": ["v0.3.11", "v0.3.13", "v0.3.15", "v0.3.15.2", "v0.3.15.4"],
                    "session_ids": [r["session_id"] for r in ss], "seeds": [r["seed"] for r in ss],
                    "episode_ids": [r["episode_id"] for r in ee],
                    "benign_variant_ids": sorted({r["variant_id"] for r in ee if r["kind"] == "benign"}),
                    "attack_variant_ids": sorted({r["variant_id"] for r in ee if r["kind"] == "attack"}),
                    "parameter_vector_sha256": [r["parameter_vector_sha256"] for r in ee],
                    "session_overlap_count": 0, "seed_overlap_count": 0, "pcap_hash_overlap_count": 0,
                    "capture_id_overlap_count": 0, "episode_overlap_count": 0, "variant_overlap_count": 0,
                    "exact_parameter_overlap_count": 0}
    write_json(REPORT / "independence_manifest.json", independence)
    commitment = {"schema_version": "v03155_label_vault_commitment_v1", "sealed_before_first_capture": True,
                  "label_vault_sha256": sha(RUNTIME / "label_vault.json"), "record_count": 3800,
                  "label_vault_git_inclusion_permitted": False, "unlock_count": 0}
    write_json(REPORT / "label_vault_commitment.json", commitment)
    hashes = {name: sha(CFG / name) for name in ["campaign.yaml", "session_manifest.yaml", "episode_schedule.yaml", "scenario_variant_manifest.yaml", "benign_variant_manifest.yaml"]}
    lock = {"schema_version": "v03155_protocol_lock_v1", "protocol_sha256": sha(PROTOCOL),
            "campaign_sha256": hashes["campaign.yaml"], "candidate_pair_lock_sha256": sha(REPORT / "candidate_pair_lock.json"),
            "independence_manifest_sha256": sha(REPORT / "independence_manifest.json"),
            "label_vault_commitment_sha256": sha(REPORT / "label_vault_commitment.json"),
            "schedule_hashes": hashes, "frozen_before_first_capture": True, "first_capture_exists": False,
            "baseline_comparator_eligible": False, "absolute_gate_promotion_branch_frozen": True}
    write_json(REPORT / "protocol_lock.json", lock)
    print(json.dumps(lock, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
