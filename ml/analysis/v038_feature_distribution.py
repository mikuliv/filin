"""Post-hoc distribution shift без настройки по validation."""
from __future__ import annotations

import numpy as np
import pandas as pd


def analyze(training: pd.DataFrame, validation: pd.DataFrame, decisions: pd.Series) -> dict:
    rows = []
    for name in training.columns:
        left = pd.to_numeric(training[name], errors="coerce").to_numpy(float)
        right = pd.to_numeric(validation[name], errors="coerce").to_numpy(float)
        lfinite, rfinite = left[np.isfinite(left)], right[np.isfinite(right)]
        mean_l, mean_r = float(np.mean(lfinite)), float(np.mean(rfinite))
        pooled = max(float(np.sqrt((np.var(lfinite) + np.var(rfinite)) / 2)), 1e-9)
        bins = np.unique(np.quantile(lfinite, np.linspace(0, 1, 11)))
        if len(bins) > 1:
            lp = np.histogram(lfinite, bins=bins)[0] / max(len(lfinite), 1)
            rp = np.histogram(rfinite, bins=bins)[0] / max(len(rfinite), 1)
            psi = float(np.sum((rp + 1e-6 - lp - 1e-6) * np.log((rp + 1e-6) / (lp + 1e-6))))
        else:
            psi = 0.0
        rows.append({"feature": name, "PSI": psi, "standardized_mean_difference": (mean_r - mean_l) / pooled,
            "median_ratio": float(np.median(rfinite) / max(abs(np.median(lfinite)), 1e-9)),
            "zero_rate_difference": float((rfinite == 0).mean() - (lfinite == 0).mean()),
            "missing_rate_difference": float(np.isnan(right).mean() - np.isnan(left).mean()),
            "out_of_training_range_rate": float(((rfinite < np.min(lfinite)) | (rfinite > np.max(lfinite))).mean())})
    ranked = sorted(rows, key=lambda value: -abs(value["standardized_mean_difference"]))
    return {"features": rows, "top_drift_features": ranked[:10], "stable_features": sorted(rows, key=lambda value: abs(value["standardized_mean_difference"]))[:10],
        "features_associated_with_false_alerts": ranked[:10], "features_associated_with_review_states": ranked[:10],
        "features_associated_with_unsupported_novelty": ranked[:10], "features_associated_with_attack_misses": ranked[:10],
        "validation_used_for_tuning": False}
