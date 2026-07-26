from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from .config import ROOT, RUNTIME

ALLOWED_ROOTS = tuple(ROOT / p for p in (
    "docs/status", "docs/experiments", "docs/research", "docs/reports", "ml/reports",
    "incident_reconstruction/contracts", "incident_reconstruction/protocols", "incident_reconstruction/rules",
    "collectors/shadow/contracts", "runtime/lab_console/logs", "runtime/lab_console/exports",
))
ALLOWED_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".txt", ".csv", ".log"}


def token_for(path: Path) -> str:
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    return base64.urlsafe_b64encode(relative.encode()).decode().rstrip("=")


def resolve_token(token: str, max_bytes: int = 1_000_000) -> Path:
    if len(token) > 1024:
        raise ValueError("invalid_file_token")
    try:
        rel = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode()
    except Exception as exc:
        raise ValueError("invalid_file_token") from exc
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError("path_traversal_rejected")
    path = (ROOT / rel).resolve(strict=True)
    if path.is_symlink() or not any(path == root.resolve() or root.resolve() in path.parents for root in ALLOWED_ROOTS if root.exists()):
        raise ValueError("file_root_rejected")
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("file_type_rejected")
    if path.stat().st_size > max_bytes:
        raise ValueError("file_too_large")
    return path


def read_safe(token: str, max_bytes: int = 1_000_000) -> dict[str, str | int]:
    path = resolve_token(token, max_bytes)
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return {"file_token": token, "content": raw.decode("utf-8"), "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
