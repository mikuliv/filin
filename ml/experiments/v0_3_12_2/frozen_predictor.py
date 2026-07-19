from __future__ import annotations
from pathlib import Path
from ml.experiments.v0_3_12.frozen_predictor import load_candidate,predict_block
from .common import sha256_file,write_json

def create_once(artifact:Path,matrix,lock,output:Path,guard):
    if output.exists():
        payload=__import__('json').loads(output.read_text(encoding="utf-8"))
        if payload.get("input_lock_sha256")==lock["input_lock_sha256"] and payload.get("record_count")==216: return payload,{"prediction_reused_on_resume":True,"prediction_generation_count":1,"prediction_sha256":sha256_file(output)}
        raise RuntimeError("Существующая v0.3.8 prediction не соответствует input lock")
    guard.authorize("v0.3.8",False); bundle=load_candidate(artifact); records,nofit=predict_block(bundle,matrix,lock["rows"],lock["benchmark_id"])
    for row in records:
        row["joint_probabilities"]=row["joint_class_probabilities"]; row["transition_reason"]=row["state_transition_reason"]
    records.sort(key=lambda r:(r["benchmark_id"],r["run_id"],r["immutable_row_id"]))
    payload={"candidate_id":bundle["candidate_id"],"benchmark_id":lock["benchmark_id"],"input_lock_sha256":lock["input_lock_sha256"],"record_count":len(records),"records":records,"true_labels_included":False}
    write_json(output,payload); return payload,{**nofit,"prediction_reused_on_resume":False,"prediction_generation_count":1,"prediction_sha256":sha256_file(output)}
