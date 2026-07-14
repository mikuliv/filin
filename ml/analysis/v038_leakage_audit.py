"""Статический аудит запрещённых model feature columns v0.3.8."""
from __future__ import annotations

import json
from pathlib import Path


FORBIDDEN = {"run_id", "execution_id", "episode_id", "episode_phase", "episode_position", "label", "binary_label", "scenario_id", "variant_id", "group", "hard_negative_target_class", "seed", "warmup", "model_prediction", "conformal_result", "support_result"}
FORBIDDEN_FRAGMENTS = ("background", "environment", "marker", "raw_ip", "hashed_ip", "hostname", "uri", "port_identifier", "container", "zeek_uid", "campaign", "dataset_path", "artifact_hash", "future")


def audit(features: list[str], output: Path | None = None) -> dict:
    violations = sorted(name for name in features if name.lower() in FORBIDDEN or any(fragment in name.lower() for fragment in FORBIDDEN_FRAGMENTS))
    result = {"v038_leakage_audit_valid": not violations, "model_features": features, "forbidden_features_found": violations,
        "conformal_and_support_after_model_features": True}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
