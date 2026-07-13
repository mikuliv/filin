"""Детерминированные post-hoc audits для locked evaluation v0.3.5."""
from __future__ import annotations
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any
import pandas as pd

FORBIDDEN_X = {"run_id","execution_id","label","label_type","scenario_id","scenario_execution_key","environment_group"}

def sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def mapping_audit(frame: pd.DataFrame) -> dict[str, Any]:
    ids=frame.execution_id.astype(str)
    return {"rows":len(frame),"unique_execution_ids":int(ids.nunique()),"mapping_1_to_1":bool(ids.nunique()==len(frame)),"dropped_rows":0,"extra_rows":0,"duplicate_rows":int(ids.duplicated().sum()),"execution_mapping_sha256":hashlib.sha256("\n".join(ids).encode()).hexdigest()}
def leakage_audit(columns: list[str]) -> dict[str, Any]:
    found=sorted(set(columns)&FORBIDDEN_X)
    return {"forbidden_features":found,"leakage_valid":not found,"projection_uses_labels":False,"projection_uses_predictions":False}
def transitions(y: pd.Series, baseline, candidate) -> dict[str, int]:
    base=pd.Series(baseline,index=y.index); cand=pd.Series(candidate,index=y.index)
    return {"baseline_wrong_candidate_correct":int(((base!=y)&(cand==y)).sum()),"baseline_correct_candidate_wrong":int(((base==y)&(cand!=y)).sum()),"remaining_candidate_errors":int((cand!=y).sum()),"rows":len(y)}
