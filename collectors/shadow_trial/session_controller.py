from __future__ import annotations

from collections import Counter, defaultdict

ATTACK_CLASSES = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon"]
LENGTHS = [2, 3, 4, 5]


def build_episode_schedule(sessions: list[dict], variants: list[str]) -> list[dict]:
    if len(sessions) != 10 or len(variants) != 20:
        raise ValueError("Требуются 10 sessions и 20 benign variants")
    occurrence = Counter()
    per_session: dict[int, list[dict]] = defaultdict(list)
    for session_index in range(10):
        present = [name for index, name in enumerate(ATTACK_CLASSES) if index != session_index % 5]
        for slot, klass in enumerate(present):
            length = LENGTHS[occurrence[klass] % 4]
            occurrence[klass] += 1
            per_session[session_index].append({"kind": "attack", "class": klass, "length": length, "slot": slot})
    for variant_index, variant in enumerate(variants):
        first_session = variant_index // 4
        second_session = 5 + ((first_session + 2) % 5)
        first_length = LENGTHS[variant_index % 4]
        second_length = LENGTHS[(variant_index + 1) % 4]
        per_session[first_session].append({"kind": "benign", "variant": variant, "class": "benign", "length": first_length})
        per_session[second_session].append({"kind": "benign", "variant": variant, "class": "benign", "length": second_length})
    result = []
    for session_index, session in enumerate(sessions):
        attacks = sorted((row for row in per_session[session_index] if row["kind"] == "attack"), key=lambda row: row["slot"])
        benign = sorted((row for row in per_session[session_index] if row["kind"] == "benign"), key=lambda row: row["variant"])
        episodes = []
        for slot, row in enumerate(benign + attacks):
            start = 12 + slot * 16
            episode_id = f"{session['session_id']}:episode:{slot + 1:02d}"
            episodes.append({**row, "episode_id": episode_id, "session_id": session["session_id"], "session_group": session["group"], "start_scored_window": start})
        result.extend(episodes)
    return result


def audit_schedule(sessions: list[dict], variants: list[str], episodes: list[dict]) -> dict:
    attack = [row for row in episodes if row["kind"] == "attack"]
    benign = [row for row in episodes if row["kind"] == "benign"]
    class_counts = Counter(row["class"] for row in attack)
    variant_counts = Counter(row["variant"] for row in benign)
    attack_lengths = Counter((row["class"], row["length"]) for row in attack)
    session_lengths = {session["session_id"]: Counter(row["length"] for row in episodes if row["session_id"] == session["session_id"] and row["kind"] == "attack") for session in sessions}
    benign_session_lengths = {session["session_id"]: Counter(row["length"] for row in episodes if row["session_id"] == session["session_id"] and row["kind"] == "benign") for session in sessions}
    variant_ok = True
    for variant in variants:
        rows = [row for row in benign if row["variant"] == variant]
        variant_ok &= len(rows) == 2 and rows[0]["length"] != rows[1]["length"] and rows[0]["session_group"] != rows[1]["session_group"]
    return {
        "episode_count": len(episodes), "attack_episode_count": len(attack), "benign_episode_count": len(benign),
        "attack_class_counts": dict(class_counts), "benign_variant_counts": dict(variant_counts),
        "attack_class_balance_passed": all(class_counts[name] == 8 for name in ATTACK_CLASSES),
        "attack_length_balance_passed": all(attack_lengths[(name, length)] == 2 for name in ATTACK_CLASSES for length in LENGTHS),
        "session_attack_length_balance_passed": all(counts == Counter(LENGTHS) for counts in session_lengths.values()),
        "session_benign_length_balance_passed": all(counts == Counter(LENGTHS) for counts in benign_session_lengths.values()),
        "benign_variant_balance_passed": variant_ok and all(variant_counts[name] == 2 for name in variants),
    }


def window_plan(session: dict, episodes: list[dict]) -> list[dict]:
    membership = {}
    for episode in episodes:
        for position in range(episode["length"]):
            membership[episode["start_scored_window"] + position] = (episode, position + 1)
    rows = []
    for capture_index in range(152):
        scored = capture_index >= 8
        scored_index = capture_index - 8
        episode, position = membership.get(scored_index, (None, None))
        klass = episode["class"] if episode else "benign"
        rows.append({
            "session_id": session["session_id"], "session_group": session["group"], "seed": session["seed"],
            "capture_index": capture_index, "window_id": f"{session['session_id']}:window:{capture_index:03d}",
            "warmup": not scored, "scored": scored, "scored_window_index": scored_index if scored else None,
            "true_class": klass, "episode_id": episode["episode_id"] if episode else None,
            "episode_kind": episode["kind"] if episode else "background", "episode_length": episode["length"] if episode else 0,
            "episode_position": position or 0, "benign_variant": episode.get("variant") if episode else None,
        })
    return rows
