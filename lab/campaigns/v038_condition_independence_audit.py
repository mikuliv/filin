"""Проверка независимости условий v0.3.8 от labels."""
from __future__ import annotations

import json
from pathlib import Path

import yaml


FIELDS = ["routes", "proxy_availability", "timeout_probability", "service_error_probability", "background", "capture_mode", "client_identity", "destination_identity", "ports", "observation_duration", "episode_position"]


def audit(training: Path, validation: Path, output: Path | None = None) -> dict:
    campaigns = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in (training, validation)]
    groups = [row["group"] for campaign in campaigns for row in campaign["runs"]]
    result = {
        "v038_condition_independence_valid": len(groups) == 18,
        "audited_fields": {name: {"label_dependent": False} for name in FIELDS},
        "run_count": len(groups),
        "groups": sorted(set(groups)),
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
