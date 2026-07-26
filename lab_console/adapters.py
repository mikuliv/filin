from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .config import ROOT
from .files import token_for
from .integrity import sha256


def load_source(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.exists():
        return {"status": "unavailable", "source": relative}
    try:
        if path.suffix == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix in {".yaml", ".yml"}:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            value = path.read_text(encoding="utf-8")
        return {"status": "verified", "source": relative, "sha256": sha256(path), "file_token": token_for(path), "value": value}
    except Exception as exc:
        return {"status": "invalid", "source": relative, "error": type(exc).__name__}


def git_value(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    except Exception:
        return "unavailable"


def project_status() -> dict[str, Any]:
    track = load_source("docs/status/v0_4_track.yaml")
    return {
        "schema_version": "console_project_status_v1", "laboratory_only": True,
        "production_ready": False, "candidate_id": "v03154:65a3dd912d845bc1",
        "mainline_stage": "v0.3.18", "mainline_next": "v0.3.19",
        "laboratory_stage": "v0.4.3", "laboratory_next": "v0.4.4",
        "backend_isolated": git_value("rev-parse", "HEAD:backend") == "04218a4eb01534950efd5f7d6390f1a575cacbc8",
        "git_head": git_value("rev-parse", "HEAD"), "tree_state": "clean" if not git_value("status", "--porcelain") else "modified",
        "source": track,
    }


def representative_sources() -> dict[str, dict[str, Any]]:
    return {name: load_source(path) for name, path in {
        "card": "ml/reports/v0_4_0/representative_incident_card.json",
        "timeline": "ml/reports/v0_4_1/representative_temporal_reconstruction.json",
        "graph": "ml/reports/v0_4_1/representative_reconstruction_graph.json",
        "hypotheses": "ml/reports/v0_4_2/representative_hypothesis_analysis.json",
        "comparisons": "ml/reports/v0_4_2/representative_comparisons.json",
        "questions": "ml/reports/v0_4_2/representative_analyst_questions.json",
    }.items()}
