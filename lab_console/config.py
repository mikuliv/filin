from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime" / "lab_console"


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8043
    token: str = ""
    development_mode: bool = False
    runtime_dir: Path = RUNTIME
    session_ttl_seconds: int = 3600
    max_view_bytes: int = 1_000_000
    max_parallel_tasks: int = 2

    def __post_init__(self) -> None:
        if self.host not in {"127.0.0.1", "localhost", "::1"} and not self.development_mode:
            raise ValueError("external_bind_rejected")
        if not 1 <= self.port <= 65535:
            raise ValueError("invalid_port")


def load_settings(host: str | None = None, port: int | None = None, *, development_mode: bool = False) -> Settings:
    token = os.environ.get("FILIN_CONSOLE_TOKEN") or secrets.token_urlsafe(32)
    return Settings(host=host or "127.0.0.1", port=port or 8043, token=token,
                    development_mode=development_mode)
