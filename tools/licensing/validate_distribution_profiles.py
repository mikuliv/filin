"""Validate the five distribution profiles and their exclusion invariants."""
from __future__ import annotations
import json
from .common import ROOT, finish, parser
EXPECTED={"source-core":"approved","laboratory-source":"approved","offline-third-party-bundle":"not_approved","model-package":"separate_license_required","dataset-package":"separate_license_required"}
FORBIDDEN={"container_images","pcap","models","datasets","runtime_databases","secrets","review_required"}
def validate(root=ROOT):
 errors=[]
 for name,status in EXPECTED.items():
  path=root/f"distribution/profiles/{name}.json"
  if not path.is_file():errors.append({"code":"distribution_profile_missing","profile":name});continue
  try:data=json.loads(path.read_text(encoding="utf-8"))
  except Exception:errors.append({"code":"distribution_profile_invalid_json","profile":name});continue
  if data.get("id")!=name:errors.append({"code":"distribution_profile_id_mismatch","profile":name})
  if data.get("status")!=status:errors.append({"code":"distribution_profile_status_invalid","profile":name})
  if status=="approved":
   if data.get("contains_images") is not False:errors.append({"code":"image_in_approved_source_profile","profile":name})
   if not FORBIDDEN.issubset(set(data.get("excludes",[]))):errors.append({"code":"approved_profile_exclusion_missing","profile":name})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_distribution_profiles",e,{"profile_count":len(EXPECTED),"profiles":EXPECTED},a.strict)
if __name__=="__main__":raise SystemExit(main())

