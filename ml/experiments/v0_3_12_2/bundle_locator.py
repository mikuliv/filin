from __future__ import annotations
from .common import ROOT,read_yaml,sha256_file
def locate(registry_path):
    registry=read_yaml(registry_path); rows=[]
    for item in registry["benchmarks"]:
        row=dict(item)
        if item["scientific_role"]=="frozen_regression":
            for key in ("source_root","validation_lock_path","feature_table_path"):
                path=ROOT/item[key]; row[key+"_exists"]=path.exists(); row[key+"_sha256"]=sha256_file(path) if path.is_file() else None
        rows.append(row)
    return {"bundle_discovery_completed":True,"benchmarks":rows}
