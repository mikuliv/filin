from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ROOT

V0471_REPORT = ROOT / "ml" / "reports" / "v0_4_7_1"
V0471_VIEWS = (
    "summary", "failed-criteria", "critical-differences", "classes", "scenarios", "sessions", "confusion-matrices",
    "confidence", "feature-availability", "feature-shift", "root-causes", "supporting-evidence", "contradicting-evidence",
    "corrective-actions", "prohibited-reuse", "autonomy", "readiness", "limitations", "export",
)


def _load(name: str, default: Any) -> Any:
    path = V0471_REPORT / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def failure_analysis(view: str = "summary") -> dict[str, Any]:
    if view not in V0471_VIEWS:
        raise KeyError("unknown_failure_analysis_view")
    criteria = _load("failure_criterion_catalog.json", {"criteria": []})
    differences = _load("critical_difference_catalog.json", {"differences": []})
    atlas = _load("error_atlas.json", {"groups": []})
    causes = _load("root_cause_assessments.json", {"assessments": []})
    actions = _load("corrective_action_catalog.json", {"actions": []})
    mapping = {
        "summary": _load("v0_4_7_1_policy_result.json", {}), "failed-criteria": criteria,
        "critical-differences": differences, "classes": [x for x in atlas["groups"] if x["group_kind"] == "class"],
        "scenarios": [x for x in atlas["groups"] if x["group_kind"] in {"class", "error_kind"}],
        "sessions": [x for x in atlas["groups"] if x["group_kind"] == "session"], "confusion-matrices": atlas,
        "confidence": [x for x in atlas["groups"] if x["group_kind"] == "confidence"],
        "feature-availability": _load("feature_availability_assessment.json", {}),
        "feature-shift": _load("feature_shift_assessment.json", {}), "root-causes": causes,
        "supporting-evidence": [{"cause_id": x["cause_id"], "evidence": x["observed_evidence"]} for x in causes["assessments"]],
        "contradicting-evidence": [{"cause_id": x["cause_id"], "evidence": x["contradicting_evidence"]} for x in causes["assessments"]],
        "corrective-actions": actions, "prohibited-reuse": _load("post_blind_knowledge_transfer.json", {}),
        "autonomy": _load("laboratory_autonomy_policy.json", {}), "readiness": _load("corrective_proposal_readiness_gate.json", {}),
        "limitations": {"document": "ml/reports/v0_4_7_1/known_limitations.md"},
        "export": _load("v0_4_7_1_bundle_manifest.json", {}),
    }
    return {"stage": "v0.4.7.1", "view": view, "views": V0471_VIEWS, "data": mapping[view],
            "read_only": True, "failed_validation_preserved": True, "candidate_mutation_allowed": False,
            "registration_allowed": False, "v0_4_8_allowed": False}
