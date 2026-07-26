from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass

SECRET_PATTERNS = [
    re.compile(r"(?i)(token|password|secret|authorization)(\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+\-/]+=*"),
]


def redact(value: str) -> str:
    text = value
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) + m.group(2) + "***") if m.lastindex == 3 else "Bearer ***", text)
    return text


@dataclass
class Session:
    csrf: str
    expires_at: float
    role: str = "laboratory_admin"


class SessionStore:
    def __init__(self, expected_token: str, ttl: int = 3600) -> None:
        self.expected_hash = hashlib.sha256(expected_token.encode()).digest()
        self.ttl = ttl
        self.sessions: dict[str, Session] = {}
        self.attempts: defaultdict[str, deque[float]] = defaultdict(deque)

    def authenticate(self, token: str, peer: str = "local") -> tuple[str, Session] | None:
        now = time.time()
        bucket = self.attempts[peer]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 10:
            return None
        bucket.append(now)
        if not hmac.compare_digest(hashlib.sha256(token.encode()).digest(), self.expected_hash):
            return None
        sid = secrets.token_urlsafe(32)
        session = Session(secrets.token_urlsafe(24), now + self.ttl)
        self.sessions[sid] = session
        return sid, session

    def get(self, sid: str | None) -> Session | None:
        session = self.sessions.get(sid or "")
        if not session or session.expires_at <= time.time():
            self.sessions.pop(sid or "", None)
            return None
        return session

    def revoke(self, sid: str | None) -> None:
        self.sessions.pop(sid or "", None)
