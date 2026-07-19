from __future__ import annotations
from pathlib import Path
import pandas as pd
from .common import read_json, sha256_file, write_json
from .frozen_predictor import load_candidate, predict_block

SCHEMA=["benchmark_id","run_id","immutable_row_id","causal_order","gate_probability","subtype_probabilities","joint_class_probabilities","calibrated_probabilities","conformal_set","top_class","top_probability","margin","benign_probability","candidate_evidence","strong_evidence","weak_evidence","activity_key","primary_state","event_flags","alert_event_id","dedup_key","state_transition_reason"]

def create(item, lock, artifact: Path, output: Path, resume=False):
    if resume and output.exists():
        payload=read_json(output)
        if payload.get("input_lock_sha256")==lock["input_lock_sha256"] and payload.get("record_count")==lock["row_count"] and payload.get("schema")==SCHEMA:
            return payload,{"prediction_skipped_on_resume":True,"prediction_sha256":sha256_file(output)}
        raise RuntimeError("immutable prediction resume mismatch")
    X=pd.read_csv(item["feature_table_path_abs"])
    bundle=load_candidate(artifact); records,audit=predict_block(bundle,X,lock["rows"],item["benchmark_id"])
    records=sorted(records,key=lambda x:(x["benchmark_id"],x["run_id"],x["immutable_row_id"]))
    payload={"candidate_id":bundle["candidate_id"],"benchmark_id":item["benchmark_id"],"input_lock_sha256":lock["input_lock_sha256"],"schema":SCHEMA,"record_count":len(records),"records":records}
    write_json(output,payload)
    return payload,{**audit,"prediction_skipped_on_resume":False,"prediction_sha256":sha256_file(output)}

def combined_hash(predictions):
    import hashlib, json
    rows=[]
    for payload in predictions:
        rows.extend(payload["records"])
    rows.sort(key=lambda x:(x["benchmark_id"],x["run_id"],x["immutable_row_id"]))
    data=(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    return hashlib.sha256(data).hexdigest()

