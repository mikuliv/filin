from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import ROOT


def load_json(relative: str, default: Any = None) -> Any:
    try:
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def load_text(relative: str, default: str = "") -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8").strip()
    except OSError:
        return default


def short(value: str | None, length: int = 12) -> str:
    if not value:
        return "недоступно"
    return value if len(value) <= length else value[:length] + "…"


def pct(value: float | int | None) -> str:
    return "—" if value is None else f"{float(value) * 100:.1f}%"


def now_label() -> str:
    return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")


def raw(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def source(relative: str) -> dict[str, str]:
    return {"label": Path(relative).name, "path": relative}
