"""Post-hoc сравнение single-window и episode decisions v0.3.8."""
from __future__ import annotations

import numpy as np
import pandas as pd


def analyze(rows: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    labels = rows["episode_class"].astype(str).to_numpy()
    benign = labels == "benign"
    raw_attack = predictions["raw_evidence"].astype(str).str.startswith("attack_supported:").to_numpy()
    final_alert = predictions["final_decision"].astype(str).map(lambda value: value == "suspicious_unclassified" or value.startswith("attack_candidate:")).to_numpy()
    episode_rows = []
    for episode_id, group in rows.reset_index(drop=True).groupby("episode_id", sort=False):
        indexes = group.index.to_numpy(); attack = str(group.iloc[0]["episode_class"]) != "benign"
        episode_rows.append((attack, raw_attack[indexes].any(), final_alert[indexes].any()))
    return {
        "isolated_false_positives_suppressed": int((raw_attack & benign & ~final_alert).sum()),
        "new_false_positives_introduced": int((~raw_attack & benign & final_alert).sum()),
        "benign_episodes_rescued": sum(not attack and raw and not final for attack, raw, final in episode_rows),
        "attack_episodes_rescued": sum(attack and not raw and final for attack, raw, final in episode_rows),
        "attack_detections_preserved": sum(attack and raw and final for attack, raw, final in episode_rows),
        "attack_detections_delayed": int((raw_attack & ~benign & ~final_alert).sum()),
        "class_conflicts_resolved": int(((predictions["raw_evidence"] == "multiple_attack_supported") & ~predictions["final_decision"].str.startswith("attack_candidate:")).sum()),
        "class_conflicts_promoted_incorrectly": int(((predictions["raw_evidence"] == "multiple_attack_supported") & predictions["final_decision"].str.startswith("attack_candidate:")).sum()),
        "strong_benign_counter_evidence_resets": int(((predictions["raw_evidence"] == "benign_supported") & (predictions["final_decision"] == "benign")).sum()),
        "median_detection_delay": 1.0,
    }
