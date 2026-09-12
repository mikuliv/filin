"""Вымышленные HTTP-цели только для внутренней сети Docker-лаборатории."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


MODE = os.environ.get("FILIN_TARGET_MODE", "http")
PORT = 8081 if MODE == "auth" else 8080
LOG_DIR = Path("/artifacts/target")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / f"{MODE}.jsonl"
TEST_ACCOUNTS = {"alex": "correct-horse", "maria": "blue-orchid", "sam": "paper-kite", "dana": "amber-lake"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args: object) -> None:
        return

    def reply(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def append_log(self, row: dict[str, object]) -> None:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def do_GET(self) -> None:  # noqa: N802
        known = {"/", "/status", "/docs", "/api/items", "/api/pulse", "/admin"}
        status = 200 if self.path in known else 404
        body = json.dumps({"status": "ok" if status == 200 else "not_found", "path": self.path}).encode()
        self.append_log({"timestamp": utc_now(), "remote_ip": self.client_address[0], "method": "GET", "path": self.path, "status_code": status})
        self.reply(status, body)

    def do_POST(self) -> None:  # noqa: N802
        size = min(int(self.headers.get("Content-Length", "0")), 4096)
        values = parse_qs(self.rfile.read(size).decode("utf-8", "replace"))
        account = (values.get("account") or values.get("user") or [""])[0]
        secret = (values.get("secret") or values.get("password") or [""])[0]
        success = MODE == "auth" and account in TEST_ACCOUNTS and TEST_ACCOUNTS[account] == secret
        status = 200 if success else 401
        self.append_log({"timestamp": utc_now(), "remote_ip": self.client_address[0], "account": account, "success": success, "failure_reason": "none" if success else "invalid_credentials", "path": self.path, "status_code": status})
        self.reply(status, b'{"accepted":true}' if success else b'{"accepted":false}')


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
