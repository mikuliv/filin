from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_13"
RUNTIME = ROOT / "lab/output/v0_3_13"
CLASSES = ("benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon")
ATTACK_CLASSES = CLASSES[1:]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_json(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_yaml(path: Path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=lambda item: item.item() if hasattr(item, "item") else str(item)) + "\n", encoding="utf-8", newline="\n")


def canonical_label(value: str) -> str:
    return "beacon" if str(value) == "beacon_simulation" else str(value)
