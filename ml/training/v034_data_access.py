"""Enforce the v0.3.4 data-isolation contract before loading any CSV."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


def policy_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_policy(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def assert_allowed_dataset(path: Path, policy: dict) -> None:
    normalized = path.as_posix().lower()
    blocked_roots = [str(root).replace("\\", "/").lower() for root in policy.get("blocked_data_roots", [])]
    prefixes = [str(prefix).lower() for prefix in policy.get("blocked_run_prefixes", [])]
    if any(root in normalized for root in blocked_roots) or any(prefix in path.name.lower() for prefix in prefixes):
        raise ValueError("v0.3.3 data are blocked from v0.3.4 training and model selection")


def assert_allowed_campaign(campaign_id: str, role: str, policy: dict) -> None:
    allowed = policy.get("allowed_training_campaigns" if role == "training" else "allowed_validation_campaigns", [])
    if campaign_id not in allowed:
        raise ValueError(f"Campaign {campaign_id} is not allowed for {role}")
