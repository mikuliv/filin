"""Inventory Docker/Compose references, system packages and mutable pins without pulling images."""
from __future__ import annotations

import json
import re
import subprocess

from .common import ROOT, dump, finish, parser, tracked

IMAGE_LICENSES={"python":"PSF-2.0","nginx":"BSD-2-Clause","suricata":"GPL-2.0-only","zeek":"BSD-3-Clause","docker.elastic.co":"Elastic-License-2.0"}
EXTERNAL=("suricata","elasticsearch","kibana","filebeat","zeek")


def mutable(ref:str)->list[str]:
    value=ref.strip().strip('"\'')
    if "@sha256:" in value:return []
    tail=value.rsplit("/",1)[-1]
    if ":" not in tail:return ["image_without_tag"]
    tag=tail.rsplit(":",1)[1]
    if tag=="latest":return ["image_latest"]
    if re.fullmatch(r"v?\d+",tag):return ["floating_major_tag"]
    return []


def local_images()->set[str]:
    try:
        p=subprocess.run(["docker","image","ls","--format","{{json .}}"],cwd=ROOT,text=True,encoding="utf-8",errors="replace",capture_output=True,timeout=20)
        if p.returncode:return set()
        out=set()
        for line in p.stdout.splitlines():
            try:
                row=json.loads(line); out.add(f"{row.get('Repository')}:{row.get('Tag')}")
            except json.JSONDecodeError: pass
        return out
    except (OSError,subprocess.TimeoutExpired):return set()


def audit()->tuple[list[dict],dict]:
    declarations=[]; apt=[]; findings=[]; local=local_images()
    for path in tracked():
        name=(ROOT/path).name.lower()
        if not (name.startswith("dockerfile") or (path.endswith((".yml",".yaml")) and ("compose" in name or path.startswith(".github/workflows/")))):continue
        text=(ROOT/path).read_text(encoding="utf-8",errors="replace")
        for no,line in enumerate(text.splitlines(),1):
            match=re.match(r"\s*FROM\s+(?:--platform=\S+\s+)?([^\s]+)",line,re.I) or re.match(r"\s*image:\s*([^\s#]+)",line,re.I)
            if match:
                ref=match.group(1); low=ref.lower(); external=any(x in low for x in EXTERNAL)
                kind="base_image" if line.lstrip().upper().startswith("FROM") else "compose_image"
                license_expression=next((v for k,v in IMAGE_LICENSES.items() if k in low),"NOASSERTION")
                mut=mutable(ref)
                row={"path":path,"line":no,"reference":ref,"kind":kind,"mutable_findings":mut,"local_available":ref in local,"verification":"local_metadata_only" if ref in local else "not_available_offline","upstream":ref.split(':')[0],"license_expression":license_expression,"included_in_distribution":False,"user_pulled":external,"optional":external,"review_required":False}
                declarations.append(row)
                for code in mut:findings.append({"code":code,"path":path,"line":no,"reference":ref,"release_effect":"excluded_reference_only"})
            if re.search(r"\b(?:apt-get|apt)\s+install\b",line):
                apt.append({"path":path,"line":no,"command":line.strip(),"license_verification":"base-distribution-package-metadata-at-build-time","included_in_distribution":False,"review_required":False})
        for no,line in enumerate(text.splitlines(),1):
            m=re.search(r"uses:\s*([^\s]+)",line)
            if m and "@" not in m.group(1): findings.append({"code":"action_without_ref","path":path,"line":no,"reference":m.group(1)})
            elif m and m.group(1).endswith("@main"): findings.append({"code":"action_main","path":path,"line":no,"reference":m.group(1)})
    errors=[]
    for row in declarations:
        if row["license_expression"]=="NOASSERTION" and row["included_in_distribution"]: errors.append({"code":"unknown_included_container_license","reference":row["reference"]})
    details={"declaration_count":len(declarations),"system_package_command_count":len(apt),"local_image_count":len(local),"declarations":declarations,"system_packages":apt,"mutable_findings":findings,"network_used":False,"docker_pull_performed":False,"policy":{"suricata":"optional_excluded","elastic_stack":"optional_user_pulled_excluded","zeek":"third_party_excluded","docker_desktop":"external_development_tool"}}
    return errors,details


def main()->int:
    args=parser(__doc__).parse_args(); errors,details=audit(); dump("docs/licensing/container-images.json",details)
    return finish("inventory_container_images",errors,{k:v for k,v in details.items() if k not in {"declarations","system_packages"}},args.strict)


if __name__=="__main__":raise SystemExit(main())
