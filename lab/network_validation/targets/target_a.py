from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    server_version = "ValidationTargetA/1"

    def _serve(self) -> None:
        if self.path.startswith("/auth/") or self.path.startswith("/session"):
            status = 401
        elif self.path.startswith("/.env") or self.path.startswith("/admin"):
            status = 404
        else:
            status = 200
        if self.path.startswith("/delayed"):
            time.sleep(0.05)
        body = json.dumps({"status": status, "path": self.path}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = _serve
    do_POST = _serve
    do_HEAD = _serve

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
