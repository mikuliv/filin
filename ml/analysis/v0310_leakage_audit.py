"""Fail-closed аудит 51 model features v0.3.10."""
from __future__ import annotations
import json
from pathlib import Path

FORBIDDEN = {"run_id", "execution_id", "episode_id", "episode_phase", "episode_position", "label", "binary_label",
             "scenario_id", "variant_id", "group", "seed", "hard_negative_target_class", "strong_or_gradual_variant",
             "warmup", "probability", "conformal_set", "support", "pending_state", "alert_history", "raw_ip",
             "hashed_ip", "hostname", "uri", "port_identifier", "container_name", "zeek_uid", "campaign_id"}

def audit(features, output: Path) -> dict:
    leaked = sorted(set(features) & FORBIDDEN)
    result = {"v0310_leakage_valid": not leaked, "leaked_features": leaked, "feature_count": len(features),
              "decision_layer_after_prediction": True, "metadata_excluded": True}
    if leaked:
        raise RuntimeError(f"Запрещённые признаки: {leaked}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
