"""Validate deterministic REUSE.toml coverage and manifest license assignments."""
from __future__ import annotations
import tomllib
from .common import ROOT, classify, finish, parser, tracked
def validate(root=ROOT):
 errors=[]; path=root/"REUSE.toml"
 if not path.is_file():return [{"code":"reuse_toml_missing"}]
 try:data=tomllib.loads(path.read_text(encoding="utf-8"))
 except Exception as exc:return [{"code":"reuse_toml_invalid","detail":str(exc)}]
 if data.get("version")!=1:errors.append({"code":"reuse_version_invalid"})
 annotations=data.get("annotations",[])
 if not any("**" in a.get("path",[]) for a in annotations):errors.append({"code":"reuse_default_coverage_missing"})
 if not any(a.get("precedence")=="override" and "**/*.md" in a.get("path",[]) and a.get("SPDX-License-Identifier")=="CC-BY-4.0" for a in annotations):errors.append({"code":"reuse_documentation_override_missing"})
 expected={
  "LICENSE":("Mozilla Foundation and contributors","MPL-2.0"),
  "LICENSES/MPL-2.0.txt":("Mozilla Foundation and contributors","MPL-2.0"),
  "LICENSES/CC-BY-4.0.txt":("Creative Commons","CC-BY-4.0"),
  "DCO.txt":("The Linux Foundation and contributors","LicenseRef-DCO-1.1"),
 }
 for target,(holder,license_id) in expected.items():
  matches=[a for a in annotations if target in a.get("path",[])]
  if len(matches)!=1:errors.append({"code":"reuse_upstream_assignment_ambiguous","path":target});continue
  row=matches[0]
  if row.get("precedence")!="override" or row.get("SPDX-FileCopyrightText")!=holder or row.get("SPDX-License-Identifier")!=license_id:errors.append({"code":"reuse_upstream_assignment_invalid","path":target})
 for p in tracked(include_untracked=True):
  row=classify(p)
  if not row["license_expression"]:errors.append({"code":"file_without_license_assignment","path":p})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_reuse_mapping",e,{"candidate_file_count":len(tracked(include_untracked=True))},a.strict)
if __name__=="__main__":raise SystemExit(main())
