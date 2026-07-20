from __future__ import annotations
import hashlib, json, math

VOLATILE = {"event_created_at", "event_observed_at"}

def _clean(value):
    if isinstance(value, float):
        if not math.isfinite(value): raise ValueError("NaN и Infinity запрещены")
        return float(format(value, ".12g"))
    if isinstance(value, dict): return {key: _clean(value[key]) for key in sorted(value)}
    if isinstance(value, list): return [_clean(item) for item in value]
    return value

def canonical_bytes(event: dict, *, identity: bool = False) -> bytes:
    omitted = VOLATILE | ({"event_hash"} if not identity else {"event_hash", "previous_event_hash"})
    value = {key: item for key, item in event.items() if key not in omitted}
    return json.dumps(_clean(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def sha256(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()

def deterministic_id(parts) -> str:
    return sha256(json.dumps(list(parts), ensure_ascii=False, separators=(",", ":")))
