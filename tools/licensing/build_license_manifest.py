"""Build frozen mappings, repository license manifest, notices and SPDX-compatible SBOMs."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .common import ROOT, classify, dump, forbidden_text, load, parser, protected_rows, sha256, tracked

MANIFEST="licensing/repository-license-manifest.json"


def files_for_build()->list[str]:
    return [p for p in tracked(include_untracked=True) if not p.endswith((".pyc",".pyo")) and "__pycache__" not in p and p != MANIFEST]


def build_frozen()->dict:
    rows=[]
    for item in protected_rows():
        path=item["path"].replace("\\","/"); assignment=classify(path)
        rows.append({"path":path,"sha256":sha256(ROOT/path),"license_expression":assignment["license_expression"],"copyright_holder":assignment["copyright_holder"],"file_type":assignment["file_type"],"assignment_source":"reuse_toml","distribution_profile":assignment["distribution_profiles"],"protecting_manifests":item.get("protecting_manifests",[])})
    payload={"schema_version":"filin_frozen_spdx_mapping_v1","protected_count":len(rows),"files":rows}
    dump("docs/licensing/frozen-spdx-mapping.json",payload); return payload


def self_digest(payload:dict)->str:
    clone=json.loads(json.dumps(payload));
    for row in clone["files"]:
        if row["path"]==MANIFEST: row["sha256"]="SELF"
    return hashlib.sha256((json.dumps(clone,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()).hexdigest()


def build_manifest()->dict:
    rows=[]
    for path in files_for_build(): rows.append({"path":path,"sha256":sha256(ROOT/path),**classify(path)})
    rows.append({"path":MANIFEST,"sha256":"SELF",**classify(MANIFEST)})
    rows.sort(key=lambda x:x["path"])
    conflicts=sum(bool(x.get("upstream_standard_text")) and (x.get("ownership")!="upstream_standard_text" or not x.get("third_party") or x.get("project_authored")) for x in rows)
    summary={"tracked_file_count":len(rows),"assigned_file_count":len(rows),"unassigned_file_count":0,
             "unknown_license_file_count":sum(x["license_expression"] in {"","NOASSERTION"} for x in rows),
             "review_required_file_count":sum(bool(x["review_required"]) for x in rows),
             "classification_conflict_count":conflicts,"upstream_standard_text_count":sum(bool(x.get("upstream_standard_text")) for x in rows)}
    payload={"schema_version":"filin_repository_license_manifest_v1_1","manifest_schema":"licensing/repository-license-manifest.schema.json","baseline_commit":"4948af7434c8e7b38731d8df8aae0b3360f2badf","self_hash_mode":"canonical_json_with_self_sha_set_to_SELF","summary":summary,"files":rows}
    digest=self_digest(payload)
    next(x for x in rows if x["path"]==MANIFEST)["sha256"]=digest
    dump(MANIFEST,payload); return payload


def spdx_header(name:str,namespace:str)->dict:
    return {"spdxVersion":"SPDX-2.3","dataLicense":"CC0-1.0","SPDXID":"SPDXRef-DOCUMENT","name":name,"documentNamespace":namespace,"creationInfo":{"created":"2026-07-27T00:00:00Z","creators":["Tool: tools.licensing.build_license_manifest"]}}


def build_sbom(manifest:dict)->None:
    repo=spdx_header("Filin repository source inventory","https://filin.local/spdx/repository/4948af7")
    repo["files"]=[{"fileName":"./"+r["path"],"SPDXID":"SPDXRef-File-"+hashlib.sha256(r["path"].encode()).hexdigest()[:16],"checksums":[{"algorithm":"SHA256","checksumValue":r["sha256"]}],"fileTypes":["TEXT"] if r["file_type"] in {"license_text","policy_text","documentation"} else ["SOURCE"],"licenseConcluded":r["license_expression"],"licenseInfoInFiles":[r["license_expression"]],"copyrightText":r["copyright_holder"] or "NOASSERTION","comment":json.dumps({"ownership":r["ownership"],"upstream_standard_text":r.get("upstream_standard_text",False),"project_authored":r.get("project_authored",False)},ensure_ascii=False)} for r in manifest["files"]]
    dump("sbom/repository.spdx.json",repo)
    deps=load("docs/licensing/python-dependencies-resolved.json") if (ROOT/"docs/licensing/python-dependencies-resolved.json").exists() else {"packages":[]}
    py=spdx_header("Filin local Python dependency inventory","https://filin.local/spdx/python/2026-07-27")
    py["packages"]=[{"name":p["name"],"SPDXID":"SPDXRef-Package-"+repl(p["name"]),"versionInfo":p["version"],"downloadLocation":"NOASSERTION","filesAnalyzed":False,"licenseConcluded":p["license_expression"],"licenseDeclared":p["license_expression"],"copyrightText":"NOASSERTION","primaryPackagePurpose":"LIBRARY"} for p in deps.get("packages",[])]
    py["comment"]="Local environment snapshot; no network resolution performed."; dump("sbom/python-environment.spdx.json",py)
    containers=load("docs/licensing/container-images.json") if (ROOT/"docs/licensing/container-images.json").exists() else {"declarations":[]}
    con=spdx_header("Filin container declaration inventory","https://filin.local/spdx/containers/2026-07-27")
    con["packages"]=[{"name":x["reference"],"SPDXID":"SPDXRef-Container-"+hashlib.sha256((x["path"]+str(x["line"])+x["reference"]).encode()).hexdigest()[:16],"downloadLocation":"NOASSERTION","filesAnalyzed":False,"licenseConcluded":x["license_expression"],"licenseDeclared":x["license_expression"],"copyrightText":"NOASSERTION","primaryPackagePurpose":"CONTAINER","comment":json.dumps({"optional":x["optional"],"included":x["included_in_distribution"],"verification":x["verification"]},ensure_ascii=False)} for x in containers.get("declarations",[])]
    dump("sbom/container-declarations.spdx.json",con)


def repl(value:str)->str:return ''.join(c if c.isalnum() or c in '.-' else '-' for c in value)


def build_notices()->None:
    deps=load("docs/licensing/python-dependencies-resolved.json").get("packages",[])
    containers=load("docs/licensing/container-images.json").get("declarations",[])
    lines=["# Уведомления о сторонних компонентах","","Этот файл — техническая инвентаризация; условия определяются upstream license каждого компонента.","","## Python packages","","| package | version | license | включён в source |","|---|---:|---|---|" ]
    lines += [f"| {p['name']} | {p['version']} | `{p['license_expression']}` | нет, устанавливается отдельно |" for p in deps]
    lines += ["","## Container references","","| reference | license | availability | distribution |","|---|---|---|---|" ]
    lines += [f"| `{x['reference']}` | `{x['license_expression']}` | {x['verification']} | excluded; reference only |" for x in containers]
    lines += ["","## Официальные standard texts","","MPL-2.0, CC BY 4.0 и DCO 1.1 включены неизменёнными как `upstream_standard_text`; это не собственные произведения проекта.","","## Особые компоненты","","Suricata (GPL-2.0-only), Elastic stack (Elastic-License-2.0), Zeek, Docker Desktop, base images и системные пакеты не являются собственным кодом «Филина» и исключены из source distribution.",""]
    (ROOT/"THIRD_PARTY_NOTICES.md").write_text("\n".join(lines),encoding="utf-8")


def main()->int:
    parser(__doc__).parse_args(); build_frozen(); build_notices(); manifest=build_manifest()
    from .validate_upstream_standard_texts import write_registry
    write_registry(ROOT, manifest); manifest=build_manifest(); build_sbom(manifest)
    # Rebuild after generated SBOM/notices exist so the manifest covers final worktree.
    manifest=build_manifest(); print(json.dumps(manifest["summary"],ensure_ascii=False,indent=2)); return 0


if __name__=="__main__":raise SystemExit(main())
