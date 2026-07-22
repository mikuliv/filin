from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

REQUIRED_ROLES = {
    "policy_result", "summary", "historical_integrity", "evidence_inventory",
    "episode_ledger", "root_cause_matrix", "claim_ledger", "test_report",
    "protocol", "proposed_protocol",
}
FORBIDDEN_PARTS = {"runtime", "pcap", "zeek", "spool", "checkpoint", "raw_ack", "label_vault", "feature_rows", "immutable_predictions"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(manifest_path: str | Path, detached_path: str | Path, root: str | Path) -> dict:
    root=Path(root).resolve(); manifest_path=Path(manifest_path).resolve(); detached_path=Path(detached_path).resolve()
    manifest=yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    errors=[]
    if manifest.get("schema_version")!="v03153_bundle_v1": errors.append("schema")
    detached=detached_path.read_text(encoding="utf-8").split()[0]
    if detached!=sha(manifest_path): errors.append("detached_sha")
    artifacts=manifest.get("artifacts",[]); paths=[x.get("path") for x in artifacts]
    if len(paths)!=len(set(paths)): errors.append("duplicate_paths")
    roles={x.get("role") for x in artifacts}
    if not REQUIRED_ROLES<=roles: errors.append("required_roles")
    claims_path=root/"ml/reports/v0_3_15_3/claim_evidence_ledger.json"
    claims={x["claim_id"] for x in json.loads(claims_path.read_text(encoding="utf-8"))["claims"]}
    for row in artifacts:
        relative=Path(row["path"])
        try: path=(root/relative).resolve(); path.relative_to(root)
        except ValueError: errors.append(f"path_confinement:{row['path']}"); continue
        if not path.is_file(): errors.append(f"missing:{row['path']}"); continue
        if path.stat().st_size!=row["size"]: errors.append(f"size:{row['path']}")
        if sha(path)!=row["sha256"]: errors.append(f"hash:{row['path']}")
        if not set(row.get("claim_ids",[]))<=claims: errors.append(f"claim_reference:{row['path']}")
        lowered=row["path"].lower()
        if any(part in lowered.split("/") for part in FORBIDDEN_PARTS): errors.append(f"raw_artifact:{row['path']}")
        # Test/code artifacts intentionally contain deterministic negative privacy
        # fixtures. They are executable specifications, not evidence payloads.
        if row.get("role") not in {"behavioral_tests","instrumentation_code","bundle_validator","artifact_validator","ack_contract"}:
            text=path.read_text(encoding="utf-8",errors="ignore")
            if re.search(r"[A-Za-z]:\\(?:Users|home)\\",text): errors.append(f"absolute_path:{row['path']}")
            if re.search(r"(?i)(?:token|password|secret)\s*[=:]\s*[^\s\"']{6,}",text): errors.append(f"secret:{row['path']}")
    policy=json.loads((root/"ml/reports/v0_3_15_3/v0_3_15_3_policy_result.json").read_text(encoding="utf-8"))
    for key in ["candidate_ready_for_v0_3_16_staging_connector_readiness","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration","production_ready","automatic_enforcement_ready","external_validation_completed"]:
        if policy.get(key) is not False: errors.append(f"readiness:{key}")
    anchors=manifest.get("historical_anchors",{})
    if anchors.get("v03152_bundle_manifest_sha256")!="49e13eceb44873f593844b07d86215b36dffd96be7ebbbb75a004c08bad8dcda": errors.append("historical_anchor")
    return {"schema_version":"v03153_bundle_validation_v1","artifact_count":len(artifacts),"error_count":len(errors),"errors":errors,"bundle_validator_passed":not errors}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--manifest",required=True); parser.add_argument("--detached",required=True); parser.add_argument("--root",default="."); args=parser.parse_args()
    result=validate(args.manifest,args.detached,args.root); print(json.dumps(result,sort_keys=True))
    if not result["bundle_validator_passed"]: raise SystemExit(1)


if __name__=="__main__": main()
