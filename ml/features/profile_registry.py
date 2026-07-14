"""Single executable registry for future feature profiles."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


HERE = Path(__file__).resolve().parent
DICTIONARY_PATH = HERE / "feature_dictionary.yaml"
FUTURE_METADATA_COLUMNS = [
    "run_id", "execution_id", "scenario_execution_key", "window_index",
    "scenario_id", "label", "label_type", "execution_mode", "synthetic",
    "observation_source", "sensor_type", "feature_profile", "window_event_count",
    "window_has_events", "window_duration_seconds", "interval_source",
    "marker_interval_evidence_sha256", "campaign_id", "campaign_version",
    "campaign_role", "campaign_run_index", "campaign_seed", "scenario_variant_id",
    "scenario_parameter_hash", "environment_profile_id",
]


@lru_cache(maxsize=1)
def _dictionary() -> dict[str, Any]:
    value = yaml.safe_load(DICTIONARY_PATH.read_text(encoding="utf-8"))
    ordered = value.get("ordered_features") or []
    definitions = value.get("features") or {}
    if len(ordered) != len(set(ordered)) or set(ordered) != set(definitions):
        raise ValueError("future feature dictionary has inconsistent names")
    required = {"formula", "source_fields", "denominator_zero", "unit", "valid_range"}
    if any(required - set(definition) for definition in definitions.values()):
        raise ValueError("future feature dictionary has an incomplete definition")
    return value


def has_profile(name: str) -> bool:
    return name == _dictionary()["profile"]


def ordered_features(name: str) -> list[str]:
    if not has_profile(name):
        raise ValueError(f"unknown future feature profile: {name}")
    return list(_dictionary()["ordered_features"])


def profile_contract(name: str, builder_path: Path | None = None) -> dict[str, Any]:
    value = _dictionary()
    features = ordered_features(name)
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    contract = {
        "profile": name,
        "semantic_version": value["profile_semantic_version"],
        "feature_count": len(features),
        "ordered_features": features,
        "feature_schema_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    if builder_path is not None:
        contract["builder_sha256"] = hashlib.sha256(builder_path.read_bytes()).hexdigest()
    return contract
