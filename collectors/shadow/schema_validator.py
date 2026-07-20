from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .canonical import canonical_bytes, sha256
from .privacy import validate as validate_privacy

SCHEMA_PATH=Path(__file__).parent/"contracts/shadow_event_v1.schema.json"
SCHEMA=json.loads(SCHEMA_PATH.read_text(encoding="utf-8")); VALIDATOR=Draft202012Validator(SCHEMA)

def validate(event: dict, *, verify_hash=True) -> bool:
    errors=sorted(VALIDATOR.iter_errors(event),key=lambda e:list(e.path))
    if errors: raise ValueError("schema_validation_failed:"+errors[0].message)
    validate_privacy(event)
    limit=12288 if event["event_type"]=="alert_emitted" else 4096 if event["event_type"]=="sensor_health" else 8192
    if len(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))>limit: raise ValueError("event_size_exceeded")
    if verify_hash and event["event_hash"]!=sha256(canonical_bytes(event)): raise ValueError("event_hash_mismatch")
    return True
