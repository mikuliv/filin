from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml


REQUIRED = {
    "ml/reports/v0_3_15_4/v0_3_15_4_summary.md", "ml/reports/v0_3_15_4/v0_3_15_4_policy_result.json",
    "ml/reports/v0_3_15_4/protocol_lock.json", "ml/reports/v0_3_15_4/scenario_contract_report.json",
    "ml/reports/v0_3_15_4/feature_contract_v2.json", "ml/reports/v0_3_15_4/development_campaign_manifest.json",
    "ml/reports/v0_3_15_4/training_lock.json", "ml/reports/v0_3_15_4/pre_audit_lock.json",
    "ml/reports/v0_3_15_4/internal_audit_metrics.json", "ml/reports/v0_3_15_4/runtime_regression_report.json",
    "ml/reports/v0_3_15_4/privacy_report.json", "ml/reports/v0_3_15_4/test_report.json",
    "ml/reports/v0_3_15_4/documentation_consistency_report.json", "ml/artifacts/v0_3_15_4/candidate_manifest.json",
    "ml/protocols/v0_3_15_4_protocol.yaml",
}
FORBIDDEN_SUFFIXES={".pcap",".pcapng",".joblib",".pkl",".pickle",".onnx"}


def sha(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(manifest_path: str|Path, detached_path: str|Path, root: str|Path) -> dict:
    root=Path(root).resolve(); manifest_path=Path(manifest_path).resolve(); detached_path=Path(detached_path).resolve(); errors=[]
    manifest=yaml.safe_load(manifest_path.read_text(encoding="utf-8")); detached=detached_path.read_text(encoding="utf-8").split()[0]
    if manifest.get("schema_version")!="v03154_bundle_v1": errors.append("schema")
    if detached!=sha(manifest_path): errors.append("detached_sha")
    rows=manifest.get("artifacts",[]); paths=[row.get("path") for row in rows]
    if len(paths)!=len(set(paths)): errors.append("duplicate_paths")
    if not REQUIRED<=set(paths): errors.append("required_paths")
    for row in rows:
        try: path=(root/row["path"]).resolve(); path.relative_to(root)
        except ValueError: errors.append("path_confinement:"+row["path"]); continue
        if not path.is_file(): errors.append("missing:"+row["path"]); continue
        if path.stat().st_size!=row["size"]: errors.append("size:"+row["path"])
        if sha(path)!=row["sha256"]: errors.append("hash:"+row["path"])
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or row["path"].startswith("runtime/"): errors.append("raw_artifact:"+row["path"])
    policy=json.loads((root/"ml/reports/v0_3_15_4/v0_3_15_4_policy_result.json").read_text(encoding="utf-8"))
    if not policy.get("v03154_redevelopment_passed") or not policy.get("candidate_ready_for_v0_3_15_5_prospective_evaluation"): errors.append("stage_result")
    for key in ["candidate_ready_for_v0_3_16_staging_connector_readiness","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration","production_ready","automatic_enforcement_ready","external_validation_completed"]:
        if policy.get(key) is not False: errors.append("readiness:"+key)
    return {"schema_version":"v03154_bundle_validation_v1","artifact_count":len(rows),"error_count":len(errors),"errors":errors,"bundle_validator_passed":not errors}


def main()->None:
    parser=argparse.ArgumentParser(); parser.add_argument("--manifest",required=True); parser.add_argument("--detached",required=True); parser.add_argument("--root",default="."); args=parser.parse_args()
    result=validate(args.manifest,args.detached,args.root); print(json.dumps(result,ensure_ascii=False,sort_keys=True)); raise SystemExit(0 if result["bundle_validator_passed"] else 1)


if __name__=="__main__": main()
