"""Validate repository manifest completeness, hashes, SBOM hygiene and release summary."""
from __future__ import annotations
import hashlib,json
from .common import ROOT, forbidden_text, finish, parser, sha256, tracked
MANIFEST="licensing/repository-license-manifest.json"
def validate(root=ROOT):
 errors=[];path=root/MANIFEST
 if not path.is_file():return [{"code":"repository_manifest_missing"}]
 data=json.loads(path.read_text(encoding="utf-8"));rows=data.get("files",[]); names=[x.get("path") for x in rows]
 candidates=sorted(p for p in tracked(include_untracked=True) if "__pycache__" not in p and not p.endswith((".pyc",".pyo")))
 if set(names)!=set(candidates):
  for p in sorted(set(candidates)-set(names)):errors.append({"code":"repository_manifest_file_missing","path":p})
  for p in sorted(set(names)-set(candidates)):errors.append({"code":"repository_manifest_extra_file","path":p})
 if len(names)!=len(set(names)):errors.append({"code":"repository_manifest_duplicate_path"})
 for row in rows:
  p=row.get("path"); target=root/p if p else None
  if target and target.is_file() and p!=MANIFEST and sha256(target)!=row.get("sha256"):errors.append({"code":"repository_manifest_sha_mismatch","path":p})
  if not row.get("license_expression"):errors.append({"code":"repository_manifest_license_missing","path":p})
  if row.get("review_required") and row.get("distribution_profiles"):errors.append({"code":"review_required_in_approved_release","path":p})
 summary=data.get("summary",{})
 for key in ("unassigned_file_count","unknown_license_file_count","review_required_file_count"):
  if summary.get(key)!=0:errors.append({"code":"repository_manifest_nonzero_summary","field":key,"value":summary.get(key)})
 for sbom in ("sbom/repository.spdx.json","sbom/python-environment.spdx.json","sbom/container-declarations.spdx.json"):
  target=root/sbom
  if not target.is_file():errors.append({"code":"sbom_missing","path":sbom});continue
  text=target.read_text(encoding="utf-8")
  for code in forbidden_text(text):errors.append({"code":code,"path":sbom})
  doc=json.loads(text)
  if doc.get("spdxVersion")!="SPDX-2.3":errors.append({"code":"sbom_version_invalid","path":sbom})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_manifest",e,{},a.strict)
if __name__=="__main__":raise SystemExit(main())

