from __future__ import annotations

import json
import subprocess
from pathlib import Path


def validate(root: str | Path=".") -> dict:
    root=Path(root).resolve()
    tracked=subprocess.check_output(["git","ls-files"],cwd=root,text=True).splitlines()
    allowed_runtime={"runtime/.env.example","runtime/docker-compose.demo.yml"}
    forbidden=[]
    for name in tracked:
        lower=name.lower()
        if lower.startswith("runtime/") and name not in allowed_runtime: forbidden.append(name)
        if lower.endswith((".pcap",".pcapng",".wire",".db",".sqlite")): forbidden.append(name)
        if any(piece in lower for piece in ["/raw_ack/","/zeek/","/spool/"]): forbidden.append(name)
    return {"schema_version":"v03153_artifact_exclusion_v1","tracked_count":len(tracked),"forbidden_tracked_paths":sorted(set(forbidden)),"artifact_exclusion_validator_passed":not forbidden}


if __name__=="__main__":
    result=validate(); print(json.dumps(result,sort_keys=True)); raise SystemExit(0 if result["artifact_exclusion_validator_passed"] else 1)
