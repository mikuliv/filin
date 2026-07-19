from __future__ import annotations
import hashlib,json,subprocess,unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/"ml/reports/v0_3_12_1"
def load(name): return json.loads((REPORT/name).read_text(encoding="utf-8"))
def complete_bundle(directory):
    files={}
    for name in ("features.csv","labels.csv","episodes.json","captures.json","prediction.json","policy.json"):
        path=directory/name; path.write_text(name,encoding="utf-8"); files[name]=(str(path),hashlib.sha256(path.read_bytes()).hexdigest())
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    return {"stage_id":"test","protocol_sha256":"a"*64,"campaign_manifest_sha256":"b"*64,"source_commit_sha256":head,"dependency_lock_sha256":"c"*64,
        "feature_table_path":files["features.csv"][0],"feature_table_sha256":files["features.csv"][1],"feature_count":1,"ordered_feature_names":["x"],"feature_schema_sha256":"d"*64,
        "row_count":1,"ordered_row_ids":["r1"],"row_mapping_sha256":"e"*64,"row_identity_version":"v1","run_mapping":{"r1":"run1"},"run_mapping_sha256":"f"*64,
        "causal_order_mapping":{"r1":0},"causal_order_mapping_sha256":"1"*64,"activity_key_source_fields":["run_id"],"activity_key_mapping_sha256":"2"*64,
        "label_table_path":files["labels.csv"][0],"label_table_sha256":files["labels.csv"][1],"label_schema_version":"v1","episode_mapping_path":files["episodes.json"][0],"episode_mapping_sha256":files["episodes.json"][1],"episode_mapping_created_before_prediction":True,
        "capture_manifest_path":files["captures.json"][0],"capture_manifest_sha256":files["captures.json"][1],"historical_candidate_id":"candidate","candidate_manifest_sha256":"3"*64,
        "immutable_prediction_path":files["prediction.json"][0],"immutable_prediction_sha256":files["prediction.json"][1],"prediction_schema_version":"v1","metric_policy_sha256":"4"*64,
        "policy_result_path":files["policy.json"][0],"policy_result_sha256":files["policy.json"][1],"compatibility_self_test_result":True,"regression_bundle_complete":True}

class V03121Mixin:
    def assert_result_flag(self,key,value=True): self.assertEqual(load("v0_3_12_1_audit_result.json")[key],value)
    def assert_timing(self,short,counts): self.assertEqual(load(f"{short}_episode_delay_summary.json")["alert_window_counts"],counts)
    def assert_state_zero(self,key): self.assertEqual(load("state_machine_consistency.json")[key],0)
    def assert_report_exists(self,name): self.assertTrue((REPORT/name).is_file())
