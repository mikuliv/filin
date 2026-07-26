"""Проверка manifest, отчётов и representative bundle v0.4.1."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from incident_reconstruction.temporal_validation import validate_temporal_bundle
def data(p):return p.read_bytes().replace(b"\r\n",b"\n")
def main()->int:
 report=ROOT/"ml/reports/v0_4_1";errors=[];mp=report/"v0_4_1_bundle_manifest.json";detached=(report/"v0_4_1_bundle_manifest.sha256").read_text(encoding="utf-8").split()[0]
 if hashlib.sha256(data(mp)).hexdigest()!=detached:errors.append("detached_manifest_mismatch")
 manifest=json.loads(mp.read_text(encoding="utf-8"))
 for x in manifest["artifacts"]:
  p=ROOT/x["path"]
  if not p.is_file() or len(data(p))!=x["size"] or hashlib.sha256(data(p)).hexdigest()!=x["sha256"]:errors.append("mismatch:"+x["path"])
 try:validate_temporal_bundle(json.loads((report/"representative_temporal_bundle.json").read_text(encoding="utf-8")))
 except Exception as e:errors.append("representative:"+str(e))
 policy=json.loads((report/"v0_4_1_policy_result.json").read_text(encoding="utf-8"))
 if not policy.get("v0_4_1_stage_passed"):errors.append("policy_failed")
 print(json.dumps({"bundle_validator_passed":not errors,"artifact_count":manifest["artifact_count"],"errors":errors},ensure_ascii=False,indent=2));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
