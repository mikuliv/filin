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
 allowed_ownership={"project_owned","upstream_standard_text","third_party_component","generated_project_file","separate_license_artifact"}
 required_fields={"path","sha256","file_type","ownership","copyright_holder","license_expression","assignment_source","frozen","third_party","generated","project_authored","upstream_standard_text","included_for_compliance","text_modification_allowed","distribution_profiles","review_required"}
 for row in rows:
  p=row.get("path"); target=root/p if p else None
  missing=sorted(required_fields-set(row))
  if missing:errors.append({"code":"repository_manifest_schema_fields_missing","path":p,"fields":missing})
  if target and target.is_file() and p!=MANIFEST and sha256(target)!=row.get("sha256"):errors.append({"code":"repository_manifest_sha_mismatch","path":p})
  if not row.get("license_expression"):errors.append({"code":"repository_manifest_license_missing","path":p})
  if row.get("ownership") not in allowed_ownership:errors.append({"code":"repository_manifest_ownership_invalid","path":p})
  if row.get("upstream_standard_text") and (row.get("ownership")!="upstream_standard_text" or row.get("project_authored") or row.get("third_party") is not True):errors.append({"code":"upstream_standard_text_classification_conflict","path":p})
  if row.get("review_required") and row.get("distribution_profiles"):errors.append({"code":"review_required_in_approved_release","path":p})
 self_row=next((x for x in rows if x.get("path")==MANIFEST),None)
 if self_row:
  clone=json.loads(json.dumps(data));next(x for x in clone["files"] if x.get("path")==MANIFEST)["sha256"]="SELF"
  expected=hashlib.sha256((json.dumps(clone,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()).hexdigest()
  if self_row.get("sha256")!=expected:errors.append({"code":"repository_manifest_self_hash_invalid"})
 summary=data.get("summary",{})
 for key in ("unassigned_file_count","unknown_license_file_count","review_required_file_count","classification_conflict_count"):
  if summary.get(key)!=0:errors.append({"code":"repository_manifest_nonzero_summary","field":key,"value":summary.get(key)})
 if summary.get("upstream_standard_text_count")!=sum(bool(x.get("upstream_standard_text")) for x in rows):errors.append({"code":"upstream_standard_text_count_mismatch"})
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
