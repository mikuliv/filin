from __future__ import annotations
from pathlib import Path
from .common import ROOT, read_yaml, sha256_file

def resolve(registry_path: Path) -> dict:
    registry=read_yaml(registry_path); resolved=[]
    for item in registry["benchmarks"]:
        row=dict(item); reasons=[]; paths={}
        for key in ("source_root","validation_lock_path","feature_table_path","historical_candidate_manifest_path","historical_prediction_path","historical_policy_result_path","historical_summary_path"):
            value=item.get(key)
            if value:
                path=ROOT/value; paths[key]={"path":value,"exists":path.exists(),"sha256":sha256_file(path) if path.is_file() else None}
                if not path.exists(): reasons.append(f"missing:{key}")
            else: paths[key]={"path":None,"exists":False,"sha256":None}
        row["authoritative_manifest_paths"]=paths; row["blocking_reasons"]=reasons; resolved.append(row)
    return {"benchmark_discovery_completed":True,"benchmarks":resolved}
