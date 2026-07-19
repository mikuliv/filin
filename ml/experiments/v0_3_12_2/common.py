from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
import yaml
ROOT=Path(__file__).resolve().parents[3]; REPORT=ROOT/"ml/reports/v0_3_12_2"
CLASSES=("benign","port_scan","auth_failures","web_probe","low_rate_dos","beacon")
ATTACK_CLASSES=CLASSES[1:]
def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def read_yaml(path): return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
def write_json(path,value): Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
def sha256_file(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sha256_json(value:Any): return hashlib.sha256((json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()).hexdigest()
def canonical_label(value): return "beacon" if str(value)=="beacon_simulation" else str(value)
