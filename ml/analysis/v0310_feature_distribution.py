"""Post-hoc drift и outcome association для всех 51 frozen features."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _psi(training: np.ndarray, validation: np.ndarray) -> float:
    finite = training[np.isfinite(training)]
    if not len(finite):
        return 0.0
    edges = np.unique(np.quantile(finite, np.linspace(0, 1, 11)))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    left = np.histogram(training, bins=edges)[0] / max(len(training), 1)
    right = np.histogram(validation, bins=edges)[0] / max(len(validation), 1)
    left, right = np.clip(left, 1e-6, None), np.clip(right, 1e-6, None)
    return float(np.sum((right - left) * np.log(right / left)))


def _association(frame: pd.DataFrame, mask: np.ndarray) -> list[dict]:
    if not mask.any() or mask.all():
        return []
    result = []
    for name in frame.columns:
        values = frame[name].astype(float).to_numpy()
        scale = np.nanstd(values) or 1.0
        effect = abs(float((np.nanmean(values[mask]) - np.nanmean(values[~mask])) / scale))
        result.append({"feature": name, "absolute_standardized_effect": effect})
    return sorted(result, key=lambda row: (-row["absolute_standardized_effect"], row["feature"]))[:10]


def analyze(training: pd.DataFrame, validation: pd.DataFrame, rows: pd.DataFrame, decisions: pd.DataFrame) -> dict:
    features = []
    for name in training.columns:
        tr = training[name].astype(float).to_numpy(); va = validation[name].astype(float).to_numpy()
        tr_finite, va_finite = tr[np.isfinite(tr)], va[np.isfinite(va)]
        scale = np.nanstd(tr_finite) or 1.0
        median = np.nanmedian(tr_finite) if len(tr_finite) else 0.0
        features.append({
            "feature": name, "psi": _psi(tr, va),
            "standardized_mean_difference": float((np.nanmean(va_finite) - np.nanmean(tr_finite)) / scale),
            "median_ratio": float(np.nanmedian(va_finite) / median) if median else None,
            "zero_rate_difference": float(np.mean(va == 0) - np.mean(tr == 0)),
            "missing_rate_difference": float(np.mean(~np.isfinite(va)) - np.mean(~np.isfinite(tr))),
            "out_of_training_range_rate": float(np.mean((va < np.nanmin(tr_finite)) | (va > np.nanmax(tr_finite)))) if len(tr_finite) else 0.0,
        })
    ranked = sorted(features, key=lambda row: (-row["psi"], row["feature"]))
    final = decisions.final_decision.astype(str)
    labels = rows.episode_class.astype(str).to_numpy()
    active = final.str.startswith("alert_emitted:").to_numpy()
    return {
        "feature_count": len(features), "per_feature": features,
        "top_drift_features": ranked[:10], "stable_features": list(reversed(ranked[-10:])),
        "features_associated_with_strong_detection": _association(validation, decisions.strong_attack_evidence.astype(bool).to_numpy()),
        "features_associated_with_pending": _association(validation, final.str.startswith("observe_pending:").to_numpy()),
        "features_associated_with_delayed_alerts": _association(validation, (rows.episode_position.to_numpy() > 1) & active),
        "features_associated_with_review": _association(validation, final.str.startswith("review_required:").to_numpy()),
        "features_associated_with_false_promotions": _association(validation, (labels == "benign") & active),
        "features_associated_with_false_benign_decisions": _association(validation, (labels != "benign") & final.eq("benign").to_numpy()),
        "features_associated_with_unresolved_episodes": _association(validation, (labels != "benign") & ~active),
        "training_oof_distribution_source": "same training feature rows used for grouped OOF",
        "validation_used_for_tuning": False,
    }
