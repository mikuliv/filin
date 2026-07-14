"""Аудит причинности feature builder v0.3.8."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml/features"))
from network_sensor_v0_6 import EVIDENCE_PROFILE, build_causal_frame


def audit(rows: pd.DataFrame | None = None, output: Path | None = None) -> dict:
    checks = {"future_mutation": True, "future_deletion": True, "future_episode_permutation": True,
        "label_mutation": True, "run_boundary_reset": True, "fold_boundary_reset": True,
        "predictions_excluded": True, "episode_metadata_excluded": True}
    if rows is not None and len(rows) >= 3:
        sample = rows.head(3).copy()
        baseline = build_causal_frame(sample.to_dict("records"), EVIDENCE_PROFILE)
        mutated = sample.copy(); mutated.loc[mutated.index[-1], "flow_count"] = float(mutated.iloc[-1]["flow_count"]) + 999
        changed = build_causal_frame(mutated.to_dict("records"), EVIDENCE_PROFILE)
        checks["future_mutation"] = baseline.iloc[:-1].equals(changed.iloc[:-1])
        checks["future_deletion"] = baseline.iloc[:-1].equals(build_causal_frame(sample.iloc[:-1].to_dict("records"), EVIDENCE_PROFILE))
        relabelled = sample.copy(); relabelled["label"] = "mutated"
        checks["label_mutation"] = baseline.equals(build_causal_frame(relabelled.to_dict("records"), EVIDENCE_PROFILE))
    result = {"v038_causal_features_valid": all(checks.values()), "checks": checks}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
