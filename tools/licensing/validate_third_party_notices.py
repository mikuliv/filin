"""Validate notices against current dependency/container registries."""
from __future__ import annotations
import json
from .common import ROOT, finish, parser
def validate(root=ROOT):
 p=root/"THIRD_PARTY_NOTICES.md"
 if not p.is_file():return [{"code":"third_party_notices_missing"}]
 text=p.read_text(encoding="utf-8");errors=[]
 for registry,key in [("docs/licensing/python-dependencies-resolved.json","packages"),("docs/licensing/container-images.json","declarations")]:
  if not (root/registry).is_file():continue
  for row in json.loads((root/registry).read_text(encoding="utf-8")).get(key,[]):
   token=row.get("name") or row.get("reference")
   if token and token not in text:errors.append({"code":"third_party_notice_entry_missing","component":token})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_third_party_notices",e,{},a.strict)
if __name__=="__main__":raise SystemExit(main())
