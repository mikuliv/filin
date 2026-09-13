"""Validate protected-file hashes, external SPDX mapping and fixed stage baselines."""
from __future__ import annotations
import json
from .common import BACKEND_TREE, BASELINE, CANDIDATE, ROOT, canonical_sha256, finish, git, parser, protected_rows

CORRECTION = "docs/licensing/frozen-spdx-mapping-correction-v1.json"


def _corrections(root):
 path=root/CORRECTION
 if not path.is_file():return {},[{"code":"frozen_spdx_correction_missing"}]
 data=json.loads(path.read_text(encoding="utf-8"));errors=[]
 if data.get("schema_version")!="filin_frozen_spdx_mapping_correction_v1":errors.append({"code":"frozen_spdx_correction_schema"})
 if data.get("status")!="accepted" or data.get("digest_basis")!="git_blob":errors.append({"code":"frozen_spdx_correction_status"})
 try: source_actual=canonical_sha256(root,"docs/licensing/frozen-spdx-mapping.json",data.get("source_mapping_commit",""))
 except Exception: source_actual=None
 if source_actual!=data.get("source_mapping_sha256"):errors.append({"code":"frozen_spdx_correction_provenance"})
 rows={x.get("path"):x for x in data.get("entries",[])}
 if None in rows or len(rows)!=len(data.get("entries",[])):errors.append({"code":"frozen_spdx_correction_duplicate"})
 if data.get("entry_count")!=len(rows):errors.append({"code":"frozen_spdx_correction_count"})
 return rows,errors
def validate(root=ROOT):
 errors=[]; mapping=root/"docs/licensing/frozen-spdx-mapping.json"
 if not mapping.is_file():return [{"code":"frozen_spdx_mapping_missing"}]
 data=json.loads(mapping.read_text(encoding="utf-8")); indexed={x["path"]:x for x in data.get("files",[])}; current=protected_rows();corrections,correction_errors=_corrections(root);errors.extend(correction_errors)
 for row in current:
  p=row["path"]
  actual=canonical_sha256(root,p);original=indexed.get(p);correction=corrections.get(p)
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
  for path in sorted(changed & protected & baseline_paths):errors.append({"code":"protected_file_changed","path":path})
  if git("rev-parse",BASELINE+":backend").strip()!=BACKEND_TREE:errors.append({"code":"backend_baseline_mismatch"})
  candidate_manifest=root/"ml/artifacts/v0_3_15_4/candidate_manifest.json"
  candidate_text=candidate_manifest.read_text(encoding="utf-8") if candidate_manifest.is_file() else ""
  if CANDIDATE not in candidate_text:errors.append({"code":"candidate_missing_or_changed"})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_frozen_license_mapping",e,{"protected_count":len(protected_rows()),"backend_tree":BACKEND_TREE,"candidate":CANDIDATE},a.strict)
if __name__=="__main__":raise SystemExit(main())
