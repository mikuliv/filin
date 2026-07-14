"""Классификация переходов closed-set → operational decision."""
from __future__ import annotations

from collections import Counter

import pandas as pd


def analyze(rows: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    transitions = []
    details = []
    for (_, row), (_, prediction) in zip(rows.reset_index(drop=True).iterrows(), predictions.reset_index(drop=True).iterrows()):
        label, closed, final = str(row["episode_class"]), str(prediction["closed_set_prediction"]), str(prediction["final_decision"])
        correct = closed == label
        alert = final == "suspicious_unclassified" or final.startswith("attack_candidate:")
        review = final.startswith("review_required:")
        if prediction["raw_evidence"] == "unsupported_novel":
            transition = "novel_promoted_to_alert" if alert else "novel_without_alert"
        elif str(prediction["raw_evidence"]).startswith("attack_supported:") and not alert:
            transition = "isolated_attack_evidence_suppressed"
        elif alert and label != "benign":
            transition = "attack_evidence_promoted"
        elif label != "benign" and not alert:
            transition = "attack_evidence_unresolved"
        elif correct and review:
            transition = "closed_correct_review"
        elif correct and alert and label == "benign":
            transition = "closed_correct_false_alert"
        elif correct:
            transition = "closed_correct_final_correct"
        elif review:
            transition = "closed_wrong_review"
        elif alert and label == "benign":
            transition = "closed_wrong_false_alert"
        else:
            transition = "closed_wrong_final_correct"
        transitions.append(transition)
        details.append({"execution_id": row["execution_id"], "closed_set_prediction": closed,
            "joint_probabilities": prediction["joint_probabilities"], "conformal_set": prediction["conformal_set"],
            "support_set": prediction["support_set"], "effective_set": prediction["effective_set"],
            "raw_evidence": prediction["raw_evidence"], "episode_evidence": prediction["episode_evidence"],
            "final_decision": final, "transition": transition})
    return {"counts": dict(Counter(transitions)), "windows": details}
