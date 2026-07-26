from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def normalized_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".yaml", ".yml", ".md", ".txt", ".csv", ".log", ".py", ".html", ".css", ".js"}:
        data = data.replace(b"\r\n", b"\n")
    return data


def sha256(path: Path) -> str:
    return hashlib.sha256(normalized_bytes(path)).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def semantic_sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()
