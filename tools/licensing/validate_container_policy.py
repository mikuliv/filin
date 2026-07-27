"""Validate container exclusions, local-verification claims and mutable-reference accounting."""
from __future__ import annotations
import json
from .common import ROOT, finish, parser
from .inventory_container_images import mutable
def validate(root=ROOT):
 errors=[];p=root/"docs/licensing/container-images.json"
 if not p.is_file():return [{"code":"container_inventory_missing"}]
 data=json.loads(p.read_text(encoding="utf-8")); rows=data.get("declarations",[])
 for row in rows:
  low=row.get("reference","").lower()
  if any(x in low for x in ("suricata","elasticsearch","kibana","filebeat","zeek")) and row.get("included_in_distribution"):
   errors.append({"code":"excluded_third_party_image_in_distribution","reference":row["reference"]})
  if row.get("verification") in {"verified","scanned"} and not row.get("local_available"):
   errors.append({"code":"unavailable_image_claimed_verified","reference":row["reference"]})
  if mutable(row.get("reference","")) and not row.get("mutable_findings"):
   errors.append({"code":"mutable_image_not_recorded","reference":row["reference"]})
 if data.get("docker_pull_performed") is not False:errors.append({"code":"docker_pull_during_validation"})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_container_policy",e,{},a.strict)
if __name__=="__main__":raise SystemExit(main())

