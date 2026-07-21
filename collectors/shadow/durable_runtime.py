from __future__ import annotations

import hashlib
import heapq
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .canonical import canonical_bytes, sha256
from .privacy import validate as validate_privacy
from .schema_validator import validate as validate_schema


def _durable_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    try:
        descriptor = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class RuntimeIntegrityError(ValueError):
    pass


class SpoolFull(RuntimeError):
    pass


class DurableSpool:
    schema = "shadow_integrated_spool_v1"

    def __init__(self, root: str | Path, maximum_bytes: int = 256 * 1024 * 1024):
        self.root = Path(root)
        self.maximum_bytes = maximum_bytes
        self.root.mkdir(parents=True, exist_ok=True)
        self.peak_bytes = self.size_bytes
        self.quarantined = 0

    @property
    def size_bytes(self) -> int:
        return sum(item.stat().st_size for item in self.root.glob("*.event"))

    def path_for(self, event: dict) -> Path:
        return self.root / f"{event['event_sequence']:08d}-{event['event_id']}.event"

    def append(self, event: dict) -> Path:
        validate_schema(event)
        validate_privacy(event)
        body = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        wrapper = {"schema": self.schema, "sha256": hashlib.sha256(body).hexdigest(), "size": len(body), "event": event}
        payload = (json.dumps(wrapper, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if self.size_bytes + len(payload) > self.maximum_bytes:
            raise SpoolFull("spool_capacity_exceeded")
        path = self.path_for(event)
        _durable_write(path, payload)
        self.peak_bytes = max(self.peak_bytes, self.size_bytes)
        return path

    def read(self, path: Path) -> dict:
        try:
            wrapper = json.loads(path.read_text(encoding="utf-8"))
            event = wrapper["event"]
            body = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except Exception as exc:
            raise RuntimeIntegrityError("spool_parse_error") from exc
        if wrapper.get("schema") != self.schema or wrapper.get("size") != len(body) or wrapper.get("sha256") != hashlib.sha256(body).hexdigest():
            raise RuntimeIntegrityError("spool_integrity_error")
        validate_schema(event)
        validate_privacy(event)
        return event

    def recover(self) -> list[dict]:
        return [self.read(path) for path in sorted(self.root.glob("*.event"))]

    def remove(self, event: dict) -> None:
        self.path_for(event).unlink(missing_ok=True)

    def compact(self, acknowledged: set[str]) -> int:
        removed = 0
        for path in sorted(self.root.glob("*.event")):
            event = self.read(path)
            if event["idempotency_key"] in acknowledged:
                path.unlink()
                removed += 1
        return removed


class DurableCheckpoint:
    schema = "shadow_integrated_checkpoint_v1"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.acknowledged: set[str] = set()
        self.hash_chain_root = "0" * 64
        if self.path.exists():
            self.load()

    def _payload(self) -> dict:
        core = {"schema": self.schema, "acknowledged": sorted(self.acknowledged), "hash_chain_root": self.hash_chain_root}
        return {**core, "checksum": sha256(json.dumps(core, sort_keys=True, separators=(",", ":")))}

    def load(self) -> None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            core = {key: value[key] for key in ("schema", "acknowledged", "hash_chain_root")}
        except Exception as exc:
            raise RuntimeIntegrityError("checkpoint_parse_error") from exc
        if core["schema"] != self.schema or value.get("checksum") != sha256(json.dumps(core, sort_keys=True, separators=(",", ":"))):
            raise RuntimeIntegrityError("checkpoint_integrity_error")
        self.acknowledged = set(core["acknowledged"])
        self.hash_chain_root = core["hash_chain_root"]

    def commit(self, event: dict) -> None:
        self.acknowledged.add(event["idempotency_key"])
        self.hash_chain_root = sha256(self.hash_chain_root + event["event_hash"])
        _durable_write(self.path, (json.dumps(self._payload(), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))


@dataclass(frozen=True)
class QueueDecision:
    accepted: bool
    rejected: dict | None = None
    evicted: dict | None = None
    reason: str | None = None


class DurablePriorityQueue:
    priorities = {"alert_emitted": 1, "review_required": 2, "drop_summary": 3, "decision_observation": 5, "alert_continuation": 6, "sensor_health": 7, "delivery_status": 7}

    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError("queue_capacity")
        self.capacity = capacity
        self._items: list[tuple[int, int, dict]] = []
        self._sequence = 0
        self.peak = 0
        self.lock = threading.Lock()

    def put(self, event: dict) -> QueueDecision:
        with self.lock:
            entry = (self.priorities.get(event["event_type"], 7), self._sequence, event)
            self._sequence += 1
            if len(self._items) >= self.capacity:
                worst = max(self._items)
                if entry[0] < worst[0]:
                    self._items.remove(worst)
                    heapq.heapify(self._items)
                    heapq.heappush(self._items, entry)
                    return QueueDecision(True, evicted=worst[2], reason="evicted_low_priority")
                return QueueDecision(False, rejected=event, reason="rejected_on_enqueue")
            heapq.heappush(self._items, entry)
            self.peak = max(self.peak, len(self._items))
            return QueueDecision(True)

    def get_batch(self, size: int) -> list[dict]:
        with self.lock:
            return [heapq.heappop(self._items)[2] for _ in range(min(size, len(self._items)))]

    def __len__(self) -> int:
        return len(self._items)


class ControlledTokenBucket:
    def __init__(self, rate: float, capacity: float | None = None, clock=time.monotonic):
        self.rate = float(rate)
        self.capacity = float(capacity or rate)
        self.tokens = self.capacity
        self.clock = clock
        self.last = clock()
        self.wait_seconds = 0.0

    def consume(self, amount: int) -> float:
        now = self.clock()
        elapsed = max(0.0, now - self.last)
        self.last = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        missing = max(0.0, amount - self.tokens)
        wait = missing / self.rate if self.rate else 0.0
        self.tokens = max(0.0, self.tokens - amount)
        self.wait_seconds += wait
        return wait
