"""Inventory declared and locally resolved Python dependencies and their license evidence."""
from __future__ import annotations

import ast
import importlib.metadata as md
import re
from collections import deque
from pathlib import Path
from packaging.requirements import Requirement

from .common import ROOT, dump, finish, parser, tracked

KNOWN = {
 "fastapi":"MIT","jinja2":"BSD-3-Clause","joblib":"BSD-3-Clause","pandas":"BSD-3-Clause",
 "pydantic":"MIT","pyyaml":"MIT","scikit-learn":"BSD-3-Clause","uvicorn":"BSD-3-Clause",
 "requests":"Apache-2.0","numpy":"BSD-3-Clause","scipy":"BSD-3-Clause","starlette":"BSD-3-Clause",
 "anyio":"MIT","click":"BSD-3-Clause","h11":"MIT","sniffio":"MIT","idna":"BSD-3-Clause",
 "typing-extensions":"PSF-2.0","annotated-types":"MIT","pydantic-core":"MIT","certifi":"MPL-2.0",
 "charset-normalizer":"MIT","urllib3":"MIT","python-dotenv":"BSD-3-Clause","httptools":"MIT",
 "uvloop":"MIT","watchfiles":"MIT","websockets":"BSD-3-Clause","exceptiongroup":"MIT",
 "packaging":"Apache-2.0 OR BSD-2-Clause","threadpoolctl":"BSD-3-Clause","tzdata":"Apache-2.0",
 "python-dateutil":"Apache-2.0 OR BSD-3-Clause","six":"MIT","colorama":"BSD-3-Clause",
 "markupsafe":"BSD-3-Clause","httpx":"BSD-3-Clause","httpcore":"BSD-3-Clause"
}
REQ = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*([^;#\s]*)")


def norm(name: str) -> str: return name.lower().replace("_","-").replace(".","-")


def requirements() -> list[dict]:
    rows=[]
    for path in tracked():
        if not re.search(r"(^|/)requirements[^/]*\.txt$",path): continue
        for no,line in enumerate((ROOT/path).read_text(encoding="utf-8",errors="replace").splitlines(),1):
            if not line.strip() or line.lstrip().startswith("#"): continue
            match=REQ.match(line)
            if match: rows.append({"path":path,"line":no,"declaration":line.strip(),"name":norm(match.group(1)),"constraint":match.group(2),"pinned_or_bounded":bool(match.group(2))})
    return rows


def imports() -> dict[str,list[str]]:
    result={}
    for path in tracked():
        if not path.endswith(".py"): continue
        try: tree=ast.parse((ROOT/path).read_text(encoding="utf-8",errors="replace"))
        except SyntaxError: continue
        names=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): names.update(x.name.split('.')[0] for x in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module: names.add(node.module.split('.')[0])
        for name in names: result.setdefault(name,[]).append(path)
    return result


def installed() -> dict[str,md.Distribution]:
    out={}
    for dist in md.distributions():
        name=dist.metadata.get("Name")
        if name: out[norm(name)]=dist
    return out


def spdx_for(name:str,dist:md.Distribution)->tuple[str,str,list[str]]:
    metadata=dist.metadata; evidence=[]
    expression=(metadata.get("License-Expression") or "").strip()
    if expression: return expression,"metadata:License-Expression",evidence
    if name in KNOWN: return KNOWN[name],"curated_normalization_and_installed_metadata",evidence
    license_value=(metadata.get("License") or "").strip()
    classifiers=metadata.get_all("Classifier") or []
    joined=" ".join([license_value,*classifiers]).lower()
    for token,spdx in [("apache software license","Apache-2.0"),("mit license","MIT"),("bsd license","BSD-3-Clause"),("mozilla public license 2.0","MPL-2.0"),("python software foundation license","PSF-2.0")]:
        if token in joined: return spdx,"installed_distribution_metadata",evidence
    return "NOASSERTION","unresolved",[license_value,*classifiers]


def audit() -> tuple[list[dict],dict]:
    declared=requirements(); env=installed(); roots=sorted({r["name"] for r in declared})
    queue=deque(roots); selected=set(); packages=[]; errors=[]
    while queue:
        name=norm(queue.popleft())
        if name in selected: continue
        selected.add(name); dist=env.get(name)
        if not dist:
            errors.append({"code":"declared_dependency_not_installed","package":name}); continue
        expression,source,evidence=spdx_for(name,dist)
        requires=[]
        for item in dist.requires or []:
            try:
                requirement=Requirement(item)
                # Inventory the mandatory runtime closure. Optional extras are declarations,
                # not installed transitive packages, unless another mandatory edge reaches them.
                if requirement.marker and not requirement.marker.evaluate({"extra":""}):
                    continue
                requires.append(norm(requirement.name))
            except Exception:
                m=REQ.match(item)
                if m: requires.append(norm(m.group(1)))
        packages.append({"name":name,"version":dist.version,"license_expression":expression,"license_evidence":source,"raw_evidence":evidence,"direct":name in roots,"dependencies":sorted(set(requires)),"review_required":expression=="NOASSERTION"})
        queue.extend(requires)
        if expression=="NOASSERTION": errors.append({"code":"unknown_python_license","package":name})
    for row in declared:
        if not row["pinned_or_bounded"]: errors.append({"code":"direct_dependency_without_version","path":row["path"],"package":row["name"]})
    imp=imports(); aliases={"yaml":"pyyaml","sklearn":"scikit-learn"}
    external={aliases.get(x,x) for x in imp if x in {"fastapi","jinja2","joblib","pandas","pydantic","yaml","sklearn","uvicorn","requests","numpy","scipy"}}
    missing=sorted(external-set(roots)-{d for p in packages for d in p["dependencies"]})
    for name in missing: errors.append({"code":"import_without_declaration","package":name})
    details={"declaration_files":sorted({r['path'] for r in declared}),"declarations":declared,"declared_direct_count":len(roots),"resolved_package_count":len(packages),"packages":sorted(packages,key=lambda x:x["name"]),"imports_considered":sorted(external),"review_required_count":sum(p["review_required"] for p in packages),"limitations":["Resolved inventory reflects the local environment; CI validates declarations without network access."]}
    return errors,details


def main()->int:
    args=parser(__doc__).parse_args(); errors,details=audit()
    dump("docs/licensing/python-dependencies-declared.json",{"schema_version":"filin_python_declarations_v1","declarations":details["declarations"]})
    dump("docs/licensing/python-dependencies-resolved.json",{"schema_version":"filin_python_resolved_v1","packages":details["packages"],"limitations":details["limitations"]})
    return finish("inventory_python_dependencies",errors,{k:v for k,v in details.items() if k not in {"packages","declarations"}},args.strict)


if __name__ == "__main__": raise SystemExit(main())
