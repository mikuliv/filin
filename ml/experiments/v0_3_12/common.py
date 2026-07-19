from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_12"
CLASSES = ["benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon"]
ATTACK_CLASSES = CLASSES[1:]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")

def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n")

def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()

def source_metadata(stage: str, lock: dict) -> list[dict]:
    import pandas as pd
    rows=[]
    for name in lock.get("dataset_paths", []):
        path=ROOT/name
        frame=pd.read_csv(path, usecols=lambda c: c in {"run_id","execution_id","scenario_execution_key","window_index","warmup","episode_id","episode_position","episode_class","label","variant_id","environment_group"})
        if "warmup" in frame: frame=frame.loc[~frame["warmup"].astype(bool)]
        records=frame.to_dict("records")
        if records:
            run_id=str(records[0].get("run_id","")); manifest=ROOT/"lab/output/runs"/run_id/"scenario_manifest.yaml"
            if manifest.exists():
                scenarios=read_yaml(manifest).get("scenarios",[]); times={str(x["execution_id"]):(x.get("planned_started_at"),x.get("planned_finished_at")) for x in scenarios}
                for row in records:
                    row["planned_started_at"],row["planned_finished_at"]=times.get(str(row.get("execution_id")),(None,None))
        rows.extend(records)
    return rows
