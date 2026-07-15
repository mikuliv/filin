"""Корректная post-hoc permutation interpretation frozen HGB/HGB."""
from __future__ import annotations

import numpy as np
from sklearn.inspection import permutation_importance


def _importance(model, X, y, seed=42):
    if len(X) == 0:
        return []
    result = permutation_importance(model, X, y, n_repeats=5, random_state=seed, scoring="f1_macro")
    rows = [{"feature": name, "importance_mean": float(mean), "importance_std": float(std)}
            for name, mean, std in zip(X.columns, result.importances_mean, result.importances_std)]
    return sorted(rows, key=lambda row: (-row["importance_mean"], row["feature"]))[:15]


def _ranges(X, mask):
    if not np.asarray(mask).any():
        return []
    result = []
    for name in X.columns:
        values = X.loc[mask, name].astype(float)
        result.append({"feature": name, "minimum": float(values.min()), "median": float(values.median()), "maximum": float(values.max())})
    return result


def analyze(bundle, X, rows, decisions):
    labels = rows.episode_class.astype(str).reset_index(drop=True)
    attack = labels.ne("benign")
    final = decisions.final_decision.astype(str).reset_index(drop=True)
    return {
        "method": "post_hoc_permutation_importance",
        "gate_top_features": _importance(bundle["gate"], X, attack.astype(int)),
        "subtype_top_features": _importance(bundle["subtype"], X.loc[attack], labels.loc[attack]),
        "tree_path_frequency_supported": False,
        "partial_dependence_performed": False,
        "feature_ranges_by_decision_outcome": {
            "strong_promotion": _ranges(X, decisions.strong_attack_evidence.astype(bool)),
            "pending": _ranges(X, final.str.startswith("pending:")),
            "delayed_detection": _ranges(X, (rows.episode_position.to_numpy() > 1) & final.str.startswith("active:").to_numpy()),
            "false_promotion": _ranges(X, labels.eq("benign").to_numpy() & final.str.startswith("active:").to_numpy()),
            "unresolved_episode": _ranges(X, attack.to_numpy() & ~final.str.startswith("active:").to_numpy()),
        },
        "validation_used_for_tuning": False,
    }
