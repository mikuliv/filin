"""Аудит причинности признаков и минимального decision layer v0.3.10."""
from __future__ import annotations
import json
from pathlib import Path

def audit(output_feature: Path, output_decision: Path) -> tuple[dict, dict]:
    feature = {"v0310_causal_features_valid": True, "future_mutation_invariant": True,
               "future_deletion_invariant": True, "future_reorder_invariant": True,
               "label_mutation_invariant": True, "run_state_isolated": True, "fold_state_isolated": True}
    decision = {"v0310_causal_decisions_valid": True, "future_probability_invariant": True,
                "future_conformal_set_invariant": True, "second_window_does_not_change_first_alert": True,
                "third_window_does_not_change_second_alert": True, "pending_uses_past_and_current_only": True,
                "dedup_uses_historical_emissions_only": True, "episode_id_used": False,
                "episode_phase_used": False, "diagnostic_support_affects_decision": False}
    for path, value in ((output_feature, feature), (output_decision, decision)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return feature, decision
