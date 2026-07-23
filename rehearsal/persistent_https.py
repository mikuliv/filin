from __future__ import annotations

import http.client
import json
import ssl
from typing import Callable
from urllib.parse import urlsplit


class PersistentJsonClient:
    def __init__(
        self,
        endpoint: str,
        context: ssl.SSLContext,
        timeout: float = 10,
        connection_factory: Callable[..., http.client.HTTPSConnection] = http.client.HTTPSConnection,
    ) -> None:
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("transport_endpoint_must_be_https")
        self.host = parsed.hostname
        self.port = parsed.port or 443
        self.path = parsed.path or "/"
        if parsed.query:
            self.path += f"?{parsed.query}"
        self.context = context
        self.timeout = timeout
        self.connection_factory = connection_factory
        self.connection: http.client.HTTPSConnection | None = None

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def send(self, body: bytes) -> dict:
        if self.connection is None:
            self.connection = self.connection_factory(
                self.host,
                self.port,
                context=self.context,
                timeout=self.timeout,
            )
        try:
            self.connection.request(
                "POST",
                self.path,
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                    "Connection": "keep-alive",
                },
            )
            response = self.connection.getresponse()
            payload = response.read()
            if response.status != 200:
                raise RuntimeError(f"transport_http_status:{response.status}")
            return json.loads(payload)
        except (OSError, http.client.HTTPException, RuntimeError, json.JSONDecodeError):
            self.close()
            raise
