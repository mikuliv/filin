"""Validate declared/resolved Python license registries."""
from __future__ import annotations
import json
from .common import ROOT, finish, parser
def validate(root=ROOT):
 errors=[];d=root/"docs/licensing/python-dependencies-resolved.json"
 if not d.is_file():return [{"code":"python_dependency_inventory_missing"}]
 data=json.loads(d.read_text(encoding="utf-8")); packages=data.get("packages",[])
 for p in packages:
  if p.get("license_expression") in {None,"","NOASSERTION"}:errors.append({"code":"unknown_python_license","package":p.get("name")})
  if p.get("review_required"):errors.append({"code":"python_dependency_review_required","package":p.get("name")})
 required={"jinja2","fastapi","uvicorn","pydantic","pyyaml","pandas","scikit-learn","joblib","requests"}
 missing=required-{p.get("name") for p in packages}
 for name in sorted(missing):errors.append({"code":"required_dependency_not_in_inventory","package":name})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_dependency_licenses",e,{},a.strict)
if __name__=="__main__":raise SystemExit(main())
