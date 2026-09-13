from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.integrity.git_objects import GitObjectError, git_blob_bytes, git_blob_sha256


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


def canonical_artifact(root: Path, relative: str, row: dict) -> bytes:
    if relative == "tools/audit/validate_v03154_bundle.py":
        correction = json.loads((root / "docs/licensing/frozen-spdx-mapping-correction-v2.json").read_text(encoding="utf-8"))
        entries = correction.get("entries", [])
        entry = entries[0] if len(entries) == 1 else {}
        if (correction.get("schema_version") != "filin_frozen_spdx_mapping_correction_v2"
                or correction.get("status") != "accepted"
                or entry.get("path") != relative
                or entry.get("correction_kind") != "protected_validator_superseded"
                or entry.get("old_stored_sha256") != row.get("sha256")
                or entry.get("canonical_git_blob_sha256") != git_blob_sha256(root, relative, "HEAD")):
            raise GitObjectError("v03154_validator_correction_invalid")
        historical = git_blob_bytes(root, relative, correction.get("source_mapping_commit", ""))
        if hashlib.sha256(historical).hexdigest() != row.get("sha256"):
            raise GitObjectError("v03154_validator_historical_blob_invalid")
        return historical
    if relative == "docs/status/project-status.yaml":
        correction_path = root / "docs/status/corrections/v0_3_15_4_bundle_status_snapshot.json"
        correction = json.loads(correction_path.read_text(encoding="utf-8"))
        if correction.get("schema_version") != "filin_historical_mutable_path_resolution_v1" or correction.get("status") != "accepted":
            raise GitObjectError("v03154_status_correction_invalid")
        if correction.get("manifest_path") != "ml/reports/v0_3_15_4/v0_3_15_4_bundle_manifest.yaml" or correction.get("artifact_path") != relative:
            raise GitObjectError("v03154_status_correction_scope")
        if correction.get("expected_sha256") != row.get("sha256") or correction.get("expected_size") != row.get("size"):
            raise GitObjectError("v03154_status_correction_digest")
        return git_blob_bytes(root, relative, correction.get("snapshot_commit", ""))
    return git_blob_bytes(root, relative, "HEAD")


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
        try: content=canonical_artifact(root,row["path"],row)
        except (GitObjectError,OSError,json.JSONDecodeError): errors.append("canonical_blob:"+row["path"]);continue
        if len(content)!=row["size"]: errors.append("size:"+row["path"])
        if hashlib.sha256(content).hexdigest()!=row["sha256"]: errors.append("hash:"+row["path"])
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
