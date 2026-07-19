from __future__ import annotations
import hashlib
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def inventory(root: Path, stage: str) -> dict:
    tokens={"pcap":(".pcap",),"zeek_logs":("conn.log","dns.log","http.log","ssl.log"),"raw_feature_tables":(".csv",),"schemas":("schema",),"mappings":("mapping",),"labels":("label",),"predictions":("prediction",),"model_artifacts":(".joblib",),"summaries":("summary",),"policy_results":("policy_result",)}
    stage_token=stage.replace(".","_"); candidates=[]
    for base in (root/"ml",root/"lab"):
        if not base.exists(): continue
        for p in base.rglob("*"):
            if p.is_file() and (stage_token in p.as_posix().lower() or stage.replace(".","") in p.as_posix().lower()): candidates.append(p)
    categories={k:[] for k in tokens}
    for p in candidates:
        low=p.name.lower()
        for kind,needles in tokens.items():
            if any(x in low for x in needles):
                categories[kind].append({"path":p.relative_to(root).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha256(p)})
    feature_tables=categories["raw_feature_tables"]
    frozen_51=any("frozen" in x["path"] and "feature" in x["path"] for x in feature_tables)
    return {"stage":stage,"categories":categories,"candidate_file_count":len(candidates),
            "pcap_content_opened":False,"zeek_content_processed":False,"frozen_51_feature_table_found":frozen_51,
            "activity_key_mapping_found":any("activity" in x["path"] for x in categories["mappings"]),
            "episode_mapping_found":any("episode" in x["path"] for x in categories["mappings"])}

