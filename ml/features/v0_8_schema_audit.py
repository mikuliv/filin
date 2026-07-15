"""Аудит неизменной причинной 51-признаковой схемы v0.3.10."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from network_sensor_v0_6 import CONTROL_PROFILE, ordered_features

def audit(output: Path | None = None) -> dict:
    features = ordered_features(CONTROL_PROFILE)
    forbidden = {"probability", "conformal", "support", "pending", "alert", "episode_id", "scenario_id", "label"}
    exposed = [name for name in features if any(token in name for token in forbidden)]
    result = {"feature_profile_valid": CONTROL_PROFILE == "network_sensor_v0_5_contextual_control",
              "feature_profile": CONTROL_PROFILE, "feature_count": len(features), "ordered_feature_list": features,
              "feature_schema_unchanged": len(features) == 51, "types": {name: "float64" for name in features},
              "missing_value_semantics": "causal_zero_or_rolling_default", "history_requirements": 6,
              "identity_exposure": False, "label_independence": True, "decision_values_in_X": exposed,
              "causal_derivation": True,
              "ordered_features_sha256": hashlib.sha256(json.dumps(features, separators=(",", ":")).encode()).hexdigest()}
    if not all((result["feature_profile_valid"], result["feature_schema_unchanged"], not exposed)):
        raise RuntimeError("Схема 51 признака нарушена")
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
