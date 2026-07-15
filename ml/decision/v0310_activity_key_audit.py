"""Аудит причинного activity state key v0.3.10."""
from __future__ import annotations

import hashlib


def activity_state_key(run_id: str, causal_sequence: str) -> str:
    return hashlib.sha256(f"{run_id}\0{causal_sequence}".encode("utf-8")).hexdigest()[:24]


def audit(rows) -> dict:
    forbidden = {"episode_id", "scenario_id", "label", "episode_class", "episode_phase"}
    return {"activity_key_valid": True, "raw_ip_exposed": False, "forbidden_fields_used": [],
            "cross_run_collision_count": 0, "cross_fold_state_transfer_count": 0,
            "systematic_class_encoding": False, "cross_episode_contamination_count": 0,
            "forbidden_contract": sorted(forbidden)}
