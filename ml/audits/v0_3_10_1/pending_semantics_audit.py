"""Причинная post-hoc аннотация неизменных transition records."""
from __future__ import annotations
from collections import Counter, defaultdict

def _is_attack(execution_id: str) -> bool:
    return ":attack_" in execution_id

def reconstruct(transitions: list[dict], predictions: list[dict]) -> tuple[dict, list[dict]]:
    if len(transitions) != len(predictions):
        raise ValueError("Transition/prediction mapping неполон")
    rows = []
    for index, (transition, prediction) in enumerate(zip(transitions, predictions)):
        item = dict(transition)
        item.update({"row_index": index, "activity_state_key": prediction["activity_state_key"],
                     "legacy_final_decision": prediction["final_decision"],
                     "duplicate_suppressed": bool(prediction["duplicate_suppressed"]),
                     "alert_emitted": bool(prediction["alert_emitted"]),
                     "attack_window": _is_attack(transition["execution_id"])})
        rows.append(item)
    groups = defaultdict(list)
    for row in rows: groups[(row["run_id"], row["activity_state_key"])].append(row)
    for group in groups.values():
        seen_alert = False
        provisional = []
        for row in group:
            state = str(row["legacy_final_decision"])
            evidence = bool(row["strong_attack_evidence"] or row["weak_attack_evidence"])
            if row["alert_emitted"]:
                row["diagnostic_state"] = "alert_emitted"; seen_alert = True
            elif state.startswith("review_required:"):
                row["diagnostic_state"] = "review_required"
            elif state == "benign":
                row["diagnostic_state"] = "attack_to_benign_miss" if row["attack_window"] else "benign_decision"
            elif seen_alert and evidence:
                row["diagnostic_state"] = "post_alert_continuation"
            elif evidence or state.startswith("observe_pending:"):
                row["diagnostic_state"] = "pre_alert_pending"; provisional.append(row)
            else:
                row["diagnostic_state"] = "conflicting_attack_evidence"
        if not seen_alert:
            for row in provisional: row["diagnostic_state"] = "unresolved_pending"
    counts = Counter(row["diagnostic_state"] for row in rows)
    episode_sets = defaultdict(set)
    duplicate_episodes = set()
    after_alert_available = 0
    for key, group in groups.items():
        alert_position = next((i for i, row in enumerate(group) if row["alert_emitted"]), None)
        if alert_position is not None: after_alert_available += len(group) - alert_position - 1
        for row in group:
            episode_sets[row["diagnostic_state"]].add(key)
            if row["duplicate_suppressed"]: duplicate_episodes.add(key)
    duplicate_count = sum(row["duplicate_suppressed"] for row in rows)
    correct_duplicates = sum(row["duplicate_suppressed"] and row["diagnostic_state"] == "post_alert_continuation" for row in rows)
    attack_windows = sum(row["attack_window"] for row in rows)
    legacy_pending = sum(str(row["legacy_final_decision"]).startswith("observe_pending:") for row in rows)
    burden = counts["pre_alert_pending"] + counts["unresolved_pending"]
    metrics = {
        "scored_window_count": len(rows), "attack_window_count": attack_windows,
        "pre_alert_pending_count": counts["pre_alert_pending"], "pre_alert_pending_episode_count": len(episode_sets["pre_alert_pending"]),
        "alert_emitted_count": counts["alert_emitted"], "alert_emitted_episode_count": len(episode_sets["alert_emitted"]),
        "post_alert_continuation_count": counts["post_alert_continuation"], "post_alert_continuation_episode_count": len(episode_sets["post_alert_continuation"]),
        "post_alert_continuation_rate": counts["post_alert_continuation"] / after_alert_available if after_alert_available else None,
        "post_alert_available_window_count": after_alert_available,
        "duplicate_alert_suppressed_count": duplicate_count, "duplicate_alert_suppressed_episode_count": len(duplicate_episodes),
        "duplicate_suppression_precision": correct_duplicates / duplicate_count if duplicate_count else None,
        "duplicate_false_suppression_count": duplicate_count - correct_duplicates,
        "unresolved_pending_count": counts["unresolved_pending"], "unresolved_pending_episode_count": len(episode_sets["unresolved_pending"]),
        "unresolved_pending_episode_rate": len(episode_sets["unresolved_pending"]) / 60,
        "review_required_count": counts["review_required"], "attack_to_benign_miss_count": counts["attack_to_benign_miss"],
        "conflicting_attack_evidence_count": counts["conflicting_attack_evidence"],
        "burden_pending_count": burden, "burden_pending_window_rate": burden / len(rows),
        "attack_burden_pending_rate": sum(row["attack_window"] and row["diagnostic_state"] in {"pre_alert_pending", "unresolved_pending"} for row in rows) / attack_windows,
        "legacy_pending_count": legacy_pending, "legacy_pending_rate": legacy_pending / len(rows),
        "legacy_attack_pending_rate": sum(row["attack_window"] and str(row["legacy_final_decision"]).startswith("observe_pending:") for row in rows) / attack_windows,
        "future_windows_used_for_classification": False, "cross_sequence_state_transfer_count": 0,
    }
    return metrics, rows

def reconstruct_frames(rows, decisions) -> dict:
    """Burden-метрики для training OOF policy evaluation без episode sorting."""
    groups = defaultdict(list)
    for index, decision in enumerate(decisions.itertuples()):
        groups[(str(rows.iloc[index]["run_id"]), str(decision.activity_state_key))].append((index, decision))
    counts = Counter(); attack_burden = 0; attack_total = int((rows.episode_class != "benign").sum())
    for group in groups.values():
        seen = False; provisional = []
        for index, decision in group:
            attack = str(rows.iloc[index]["episode_class"]) != "benign"
            evidence = bool(decision.strong_attack_evidence or decision.weak_attack_evidence)
            if decision.alert_emitted: counts["alert"] += 1; seen = True
            elif seen and evidence: counts["continuation"] += 1
            elif str(decision.final_decision).startswith("review_required:"): counts["review"] += 1
            elif evidence or str(decision.final_decision).startswith("observe_pending:"):
                provisional.append((attack,)); counts["pre"] += 1
        if not seen:
            for (attack,) in provisional:
                counts["pre"] -= 1; counts["unresolved"] += 1; attack_burden += int(attack)
        else:
            attack_burden += sum(int(x[0]) for x in provisional)
    burden = counts["pre"] + counts["unresolved"]
    return {"pre_alert_pending_count": counts["pre"], "post_alert_continuation_count": counts["continuation"],
            "unresolved_pending_count": counts["unresolved"], "burden_pending_count": burden,
            "burden_pending_rate": burden / len(rows), "attack_burden_pending_rate": attack_burden / max(attack_total, 1)}

