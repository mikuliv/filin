from __future__ import annotations
from .common import sha256_json,write_json
def create(datasets,output):
    entries=[]; rows=[]
    for payload in datasets:
        entries.append({"benchmark_id":payload["benchmark_id"],"record_count":payload["record_count"],"prediction_sha256":payload["prediction_sha256"],"new_prediction_generated":payload["new_prediction_generated"]})
        rows.extend(payload["records"])
    rows.sort(key=lambda r:(r["benchmark_id"],r["run_id"],r["activity_key"],r["causal_order"],r["immutable_row_id"]))
    result={"canonical_order":["benchmark_id","run_id","activity_key","causal_order","immutable_row_id"],"predictions":entries,"combined_canonical_content_sha256":sha256_json(rows)}; write_json(output,result); return result
