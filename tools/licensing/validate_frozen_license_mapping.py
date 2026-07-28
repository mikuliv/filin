"""Validate protected-file hashes, external SPDX mapping and fixed stage baselines."""
from __future__ import annotations
import json
from .common import BACKEND_TREE, BASELINE, CANDIDATE, ROOT, finish, git, parser, protected_rows, sha256
def validate(root=ROOT):
 errors=[]; mapping=root/"docs/licensing/frozen-spdx-mapping.json"
 if not mapping.is_file():return [{"code":"frozen_spdx_mapping_missing"}]
 data=json.loads(mapping.read_text(encoding="utf-8")); indexed={x["path"]:x for x in data.get("files",[])}; current=protected_rows()
 for row in current:
  p=row["path"]
  if p not in indexed:errors.append({"code":"protected_file_mapping_missing","path":p});continue
  if sha256(root/p)!=indexed[p].get("sha256"):errors.append({"code":"frozen_sha_mismatch","path":p})
  if not indexed[p].get("license_expression"):errors.append({"code":"protected_file_license_missing","path":p})
 if set(indexed)!={r["path"] for r in current}:errors.append({"code":"protected_mapping_set_mismatch"})
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
