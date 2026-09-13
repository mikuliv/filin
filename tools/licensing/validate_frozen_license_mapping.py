"""Validate protected-file hashes, external SPDX mapping and fixed stage baselines."""
from __future__ import annotations
import json
from .common import BACKEND_TREE, BASELINE, CANDIDATE, ROOT, canonical_sha256, canonical_sha256_many, finish, git, parser, protected_rows

CORRECTIONS = (
 "docs/licensing/frozen-spdx-mapping-correction-v1.json",
 "docs/licensing/frozen-spdx-mapping-correction-v2.json",
)


def _corrections(root):
 rows={};errors=[]
 for index,name in enumerate(CORRECTIONS,1):
  path=root/name
  if not path.is_file():errors.append({"code":"frozen_spdx_correction_missing","path":name});continue
  data=json.loads(path.read_text(encoding="utf-8"))
  if data.get("schema_version")!=f"filin_frozen_spdx_mapping_correction_v{index}":errors.append({"code":"frozen_spdx_correction_schema","path":name})
  if data.get("status")!="accepted" or data.get("digest_basis")!="git_blob":errors.append({"code":"frozen_spdx_correction_status","path":name})
  try: source_actual=canonical_sha256(root,"docs/licensing/frozen-spdx-mapping.json",data.get("source_mapping_commit",""))
  except Exception: source_actual=None
  if source_actual!=data.get("source_mapping_sha256"):errors.append({"code":"frozen_spdx_correction_provenance","path":name})
  items=data.get("entries",[]);current={x.get("path"):x for x in items}
  if None in current or len(current)!=len(items) or set(current)&set(rows):errors.append({"code":"frozen_spdx_correction_duplicate","path":name})
  if data.get("entry_count")!=len(current):errors.append({"code":"frozen_spdx_correction_count","path":name})
  rows.update(current)
 return rows,errors
def validate(root=ROOT):
 errors=[]; mapping=root/"docs/licensing/frozen-spdx-mapping.json"
 if not mapping.is_file():return [{"code":"frozen_spdx_mapping_missing"}]
 data=json.loads(mapping.read_text(encoding="utf-8")); indexed={x["path"]:x for x in data.get("files",[])}; current=protected_rows();corrections,correction_errors=_corrections(root);errors.extend(correction_errors)
 actual_by_path=canonical_sha256_many(root,[row["path"] for row in current])
 for row in current:
  p=row["path"]
  actual=actual_by_path[p];original=indexed.get(p);correction=corrections.get(p)
  if original and actual==original.get("sha256"):
   effective=original
  elif correction and correction.get("canonical_git_blob_sha256")==actual and correction.get("status")=="accepted":
   if original and correction.get("old_stored_sha256")!=original.get("sha256"):errors.append({"code":"frozen_spdx_correction_old_digest_mismatch","path":p})
   if not original and correction.get("correction_kind")!="mapping_entry_added":errors.append({"code":"frozen_spdx_correction_kind","path":p})
   effective=correction
  else:
   effective=original
   errors.append({"code":"protected_file_mapping_missing" if not original else "frozen_sha_mismatch","path":p})
  if not effective or not effective.get("license_expression"):errors.append({"code":"protected_file_license_missing","path":p})
 current_paths={r["path"] for r in current};effective_paths=set(indexed)|{p for p,r in corrections.items() if r.get("status")=="accepted"}
 if effective_paths!=current_paths:errors.append({"code":"protected_mapping_set_mismatch"})
 if root==ROOT:
  changed=set(git("diff","--name-only",BASELINE,"--").splitlines())
  protected={r["path"] for r in current}
  baseline_paths=set(git("ls-tree","-r","--name-only",BASELINE).splitlines())
  for path in sorted(changed & protected & baseline_paths):
   correction=corrections.get(path);original=indexed.get(path)
   if not correction or correction.get("correction_kind")!="protected_validator_superseded" or not original or correction.get("old_stored_sha256")!=original.get("sha256") or correction.get("canonical_git_blob_sha256")!=actual_by_path[path]:
    errors.append({"code":"protected_file_changed","path":path})
  if git("rev-parse",BASELINE+":backend").strip()!=BACKEND_TREE:errors.append({"code":"backend_baseline_mismatch"})
  candidate_manifest=root/"ml/artifacts/v0_3_15_4/candidate_manifest.json"
  candidate_text=candidate_manifest.read_text(encoding="utf-8") if candidate_manifest.is_file() else ""
  if CANDIDATE not in candidate_text:errors.append({"code":"candidate_missing_or_changed"})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_frozen_license_mapping",e,{"protected_count":len(protected_rows()),"backend_tree":BACKEND_TREE,"candidate":CANDIDATE},a.strict)
if __name__=="__main__":raise SystemExit(main())
