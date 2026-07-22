from __future__ import annotations

import json
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from staging.contracts import ContractError, canonical_bytes

MAX_BODY = 2 * 1024 * 1024


def server_context(cert: str, key: str, ca: str) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(cert, key)
    context.load_verify_locations(cafile=ca)
    return context


def client_context(cert: str, key: str, ca: str) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = True
    context.load_cert_chain(cert, key)
    context.load_verify_locations(cafile=ca)
    return context


def serve(host: str, port: int, context: ssl.SSLContext, routes: dict[str, Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]], health: Callable[[], bool]) -> None:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _reply(self, status: int, value: dict[str, Any]) -> None:
            body = canonical_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path not in {"/health", "/ready"}:
                self._reply(404, {"error_code": "not_found"}); return
            ready = health()
            self._reply(200 if ready else 503, {"status": "ready" if ready else "unavailable"})

        def do_POST(self) -> None:
            route = routes.get(self.path)
            if route is None:
                self._reply(404, {"error_code": "not_found"}); return
            if self.headers.get("Content-Encoding"):
                self._reply(415, {"error_code": "compression_forbidden"}); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    raise ContractError("body_size_invalid")
                value = json.loads(self.rfile.read(length))
                status, response = route(value)
                self._reply(status, response)
            except ContractError as error:
                self._reply(422, {"error_code": error.code})
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._reply(400, {"error_code": "invalid_json"})
            except Exception:
                self._reply(503, {"error_code": "temporarily_unavailable"})

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()
