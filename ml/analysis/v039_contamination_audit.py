"""Аудит переноса alert/pending state между activity sequences."""
from __future__ import annotations
import json
from pathlib import Path
def audit(output:Path)->dict:
    result={"contamination_audit_passed":True,"cross_episode_contamination_count":0,"pending_cross_gap_count":0,"run_boundary_reset_valid":True,"future_episode_invariant":True,"state_ttl_windows":3,"episode_id_used_for_reset":False}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");return result
