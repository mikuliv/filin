from __future__ import annotations
import pandas as pd
from .common import ROOT,read_yaml,sha256_file,sha256_json

def blind_rows(item):
    lock=read_yaml(ROOT/item["validation_lock_path"]); rows=[]; index=0
    for name in lock["dataset_paths"]:
        frame=pd.read_csv(ROOT/name,usecols=lambda c:c in {"run_id","execution_id","scenario_execution_key","window_index","warmup","episode_id"})
        if "warmup" in frame: frame=frame.loc[~frame["warmup"].astype(bool)]
        for record in frame.to_dict("records"):
            run=str(record["run_id"]); episode_key=str(record.get("episode_id")); activity=f"{run}:{sha256_json([run,episode_key])[:16]}"
            rows.append({"run_id":run,"immutable_row_id":sha256_json([item["benchmark_id"],run,record.get("execution_id"),record.get("window_index"),index]),"causal_order":index,"activity_key_source":activity,"episode_mapping_key":str(record.get("episode_id"))}); index+=1
    return rows

def create(item,hashes,prediction_code_sha256):
    rows=blind_rows(item); schema=read_yaml(ROOT/"ml/experiments/v0_3_11/feature_schema.yaml")["ordered_features"]; frame=pd.read_csv(ROOT/item["feature_table_path"])
    if len(rows)!=item["expected_scored_rows"] or len(frame)!=len(rows): raise RuntimeError("v0.3.8 scored row count mismatch")
    if any(x not in frame.columns for x in schema) or len(schema)!=51: raise RuntimeError("v0.3.8 feature compatibility failed")
    matrix=frame.loc[:,schema].astype(float)
    if not matrix.notna().all().all(): raise RuntimeError("v0.3.8 non-finite feature")
    payload={"benchmark_id":item["benchmark_id"],"v03122_protocol_sha256":hashes["combined_protocol"],"benchmark_registry_sha256":hashes["registry"],"coverage_policy_sha256":hashes["coverage"],"candidate_artifact_sha256":hashes["candidate_artifact"],"candidate_manifest_sha256":hashes["candidate_manifest"],"v038_campaign_manifest_sha256":sha256_file(ROOT/item["validation_lock_path"]),"v038_feature_table_sha256":sha256_file(ROOT/item["feature_table_path"]),"v038_feature_schema_sha256":hashes["feature_schema"],"v038_canonical_matrix_sha256":sha256_json({"features":schema,"rows":matrix.values.tolist()}),"v038_ordered_row_mapping_sha256":sha256_json(rows),"v038_run_mapping_sha256":sha256_json([r["run_id"] for r in rows]),"v038_causal_order_mapping_sha256":sha256_json([r["causal_order"] for r in rows]),"v038_activity_key_mapping_sha256":sha256_json([r["activity_key_source"] for r in rows]),"v038_episode_mapping_sha256":sha256_json([r["episode_mapping_key"] for r in rows]),"prediction_code_sha256":prediction_code_sha256,"dependency_lock_sha256":sha256_file(ROOT/"ml/requirements.txt"),"source_commit_sha256":"0df5568ce5935dff7dff6612e85198f10d7b18d7","scored_row_count":len(rows),"feature_count":len(schema),"ordered_feature_names":schema,"rows":rows}
    payload["input_lock_sha256"]=sha256_json({k:v for k,v in payload.items() if k!="rows"}); return payload,matrix
