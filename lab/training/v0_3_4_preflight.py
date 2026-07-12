"""Неисполняющие preflight-проверки шести фиксированных групп v0.3.4."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"lab"/"campaigns"))
from v034_campaign import build_manifest, load_campaign

GROUPS = ("standard", "mixed", "hard_negative", "environment", "composition", "shift")

def preflight(campaign_path: Path) -> dict:
    campaign=load_campaign(campaign_path); names={r["group"] for r in campaign["runs"]}
    catalog=campaign["execution_catalog"]["benign"]
    scenarios=[]
    for path in (ROOT/"lab"/"scenarios").rglob("*.yaml"):
        item=yaml.safe_load(path.read_text(encoding="utf-8")) or {}; scenarios.append(item.get("scenario_id"))
    if len(catalog)!=16 or not set(catalog).issubset(scenarios): raise ValueError("Каталог benign v0.3.4 неполон")
    if not names.issubset(set(GROUPS)): raise ValueError("Неизвестная группа campaign")
    example=build_manifest(campaign,campaign["runs"][0],ROOT/"lab"/"scenarios")
    if example["scenario_count"] != 21: raise ValueError("Preflight: требуется 21 execution")
    prefix = "train" if campaign["role"] == "training" else "validation"
    return {f"preflight_v034_{prefix}_{group}": group in names for group in names}
