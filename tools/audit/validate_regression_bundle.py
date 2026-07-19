from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import yaml

REQUIRED=("stage_id","protocol_sha256","campaign_manifest_sha256","source_commit_sha256","dependency_lock_sha256","feature_table_path","feature_table_sha256","feature_count","ordered_feature_names","feature_schema_sha256","row_count","ordered_row_ids","row_mapping_sha256","row_identity_version","run_mapping","run_mapping_sha256","causal_order_mapping","causal_order_mapping_sha256","activity_key_source_fields","activity_key_mapping_sha256","label_table_path","label_table_sha256","label_schema_version","episode_mapping_path","episode_mapping_sha256","episode_mapping_created_before_prediction","capture_manifest_path","capture_manifest_sha256","historical_candidate_id","candidate_manifest_sha256","immutable_prediction_path","immutable_prediction_sha256","prediction_schema_version","metric_policy_sha256","policy_result_path","policy_result_sha256","compatibility_self_test_result","regression_bundle_complete")
FILES=(("feature_table_path","feature_table_sha256"),("label_table_path","label_table_sha256"),("episode_mapping_path","episode_mapping_sha256"),("capture_manifest_path","capture_manifest_sha256"),("immutable_prediction_path","immutable_prediction_sha256"),("policy_result_path","policy_result_sha256"))
def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def validate(path:Path,metadata_only=False):
    data=yaml.safe_load(path.read_text(encoding="utf-8")); root=path.parent; errors=[]; warnings=[]
    errors += [f"missing_field:{k}" for k in REQUIRED if k not in data]
    if len(data.get("ordered_row_ids",[])) != len(set(data.get("ordered_row_ids",[]))): errors.append("duplicate_row_id")
    if data.get("row_count") != len(data.get("ordered_row_ids",[])): errors.append("row_count_mismatch")
    if data.get("feature_count") != len(data.get("ordered_feature_names",[])): errors.append("feature_count_mismatch")
    if not data.get("run_mapping") or set(data.get("ordered_row_ids",[]))-set(data.get("run_mapping",{})): errors.append("run_mapping_incomplete")
    if not data.get("causal_order_mapping") or set(data.get("ordered_row_ids",[]))-set(data.get("causal_order_mapping",{})): errors.append("causal_order_mapping_incomplete")
    if data.get("episode_mapping_created_before_prediction") is not True: errors.append("episode_mapping_not_pre_prediction")
    if data.get("label_table_path") == data.get("feature_table_path") or data.get("label_table_path") == data.get("immutable_prediction_path"): errors.append("label_separation_failed")
    for pkey,hkey in FILES:
        raw=data.get(pkey); expected=data.get(hkey)
        if not raw: errors.append(f"missing_path:{pkey}"); continue
        file=(root/raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if not file.exists():
            (warnings if metadata_only else errors).append(f"missing_file:{pkey}"); continue
        if expected and sha256(file)!=expected: errors.append(f"hash_mismatch:{pkey}")
    commit=data.get("source_commit_sha256")
    if commit:
        repo=Path(__file__).resolve().parents[2]
        if subprocess.run(["git","cat-file","-e",f"{commit}^{{commit}}"],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: errors.append("source_commit_missing")
    if metadata_only and data.get("regression_bundle_complete"): errors.append("metadata_only_cannot_confirm_complete")
    facts_complete=not errors and not metadata_only
    if bool(data.get("regression_bundle_complete")) != facts_complete: errors.append("bundle_complete_flag_mismatch")
    return {"valid":not errors,"metadata_only":metadata_only,"errors":errors,"warnings":warnings,"regression_bundle_complete":facts_complete}
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",type=Path,required=True); ap.add_argument("--strict",action="store_true"); ap.add_argument("--metadata-only",action="store_true"); a=ap.parse_args(argv)
    result=validate(a.manifest,a.metadata_only); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result["valid"] or not a.strict else 1
if __name__=="__main__": raise SystemExit(main())

