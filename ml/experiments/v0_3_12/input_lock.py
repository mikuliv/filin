from __future__ import annotations
from pathlib import Path
from .common import ROOT, read_yaml, sha256_file, sha256_json, source_metadata

def create(item, audit, hashes, prediction_code_sha256):
    lock=read_yaml(ROOT/item["validation_lock_path"]) if item.get("validation_lock_path") else {}
    metadata=source_metadata(item["source_stage"],lock) if lock else []
    blind=[]; last_run=None; previous_finish=None; sequence=0
    for i,row in enumerate(metadata):
        run=str(row.get("run_id",""))
        if run!=last_run: sequence=0; previous_finish=None
        elif previous_finish and row.get("planned_started_at"):
            from datetime import datetime
            start=datetime.fromisoformat(str(row["planned_started_at"]).replace("Z","+00:00")); finish=datetime.fromisoformat(str(previous_finish).replace("Z","+00:00"))
            if (start-finish).total_seconds()>60: sequence+=1
        blind.append({"run_id":run,"immutable_row_id":sha256_json([item["benchmark_id"],run,row.get("execution_id"),row.get("window_index"),i]),"causal_order":i,"activity_key_source":f"{run}:{sequence}"})
        last_run=run; previous_finish=row.get("planned_finished_at")
    return {"benchmark_id":item["benchmark_id"],"regression_protocol_sha256":hashes["protocol"],"benchmark_registry_sha256":hashes["registry"],"candidate_artifact_sha256":hashes["candidate_artifact"],"candidate_manifest_sha256":hashes["candidate_manifest"],"source_campaign_manifest_sha256":sha256_file(ROOT/item["validation_lock_path"]) if item.get("validation_lock_path") else None,"feature_table_sha256":audit["feature_table_sha256"],"canonical_feature_matrix_sha256":audit["canonical_feature_matrix_sha256"],"feature_schema_sha256":hashes["feature_schema"],"ordered_row_mapping_sha256":sha256_json(blind),"activity_key_mapping_sha256":sha256_json([x["activity_key_source"] for x in blind]),"episode_mapping_sha256":lock.get("episode_mapping_sha256"),"class_mapping_sha256":hashes["class_mapping"],"dependency_lock_sha256":sha256_file(ROOT/"ml/requirements.txt"),"source_commit_sha256":hashes["head"],"prediction_code_sha256":prediction_code_sha256,"evaluation_mode":audit["evaluation_mode"],"row_count":len(blind),"rows":blind}
