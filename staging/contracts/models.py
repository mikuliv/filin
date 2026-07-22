from __future__ import annotations

import hashlib
import json
from typing import Any

REGISTRY_COMMITMENT = "e00589bd0bcdec8cc8d1a1147905977a7434594d21f7369dc4b71166e4d6f24c"
CANDIDATE_ID = "v03154:65a3dd912d845bc1"
HEX64 = frozenset("0123456789abcdef")


class ContractError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    body = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(body).hexdigest()


def _object(value: Any, fields: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ContractError(code, "fields")
    return value


def _text(value: Any, code: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ContractError(code, "text")
    return value


def _hash(value: Any, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - HEX64:
        raise ContractError(code, "sha256")
    return value


def _events(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 50:
        raise ContractError("event_count_invalid")
    result = []
    for event in value:
        if not isinstance(event, dict):
            raise ContractError("event_schema_invalid")
        if event.get("event_contract_version") != "shadow_event_v2" or event.get("schema_version") != "shadow_event_v2":
            raise ContractError("event_contract_mismatch")
        candidate = event.get("candidate_ref")
        if not isinstance(candidate, dict) or candidate.get("candidate_id") != CANDIDATE_ID:
            raise ContractError("candidate_not_allowed")
        if candidate.get("registry_commitment_sha256") != REGISTRY_COMMITMENT:
            raise ContractError("registry_commitment_mismatch")
        _text(event.get("event_id"), "event_id_invalid")
        _text(event.get("idempotency_key"), "idempotency_key_invalid")
        result.append(event)
    return result


def validate_ingress(value: Any) -> dict[str, Any]:
    fields = {"ingress_contract_version", "request_id", "sensor_instance_id", "candidate_registry_commitment_sha256", "events", "request_body_sha256"}
    item = _object(value, fields, "ingress_schema_invalid")
    if item["ingress_contract_version"] != "connector_ingress_v1":
        raise ContractError("ingress_contract_mismatch")
    _text(item["request_id"], "request_id_invalid")
    _text(item["sensor_instance_id"], "sensor_instance_id_invalid")
    if item["candidate_registry_commitment_sha256"] != REGISTRY_COMMITMENT:
        raise ContractError("registry_commitment_mismatch")
    _events(item["events"])
    expected = digest({key: val for key, val in item.items() if key != "request_body_sha256"})
    if _hash(item["request_body_sha256"], "request_body_hash_invalid") != expected:
        raise ContractError("request_body_hash_mismatch")
    return item


def validate_batch(value: Any) -> dict[str, Any]:
    fields = {"batch_contract_version", "batch_id", "attempt_id", "connector_instance_id", "candidate_registry_commitment_sha256", "event_contract_version", "events", "event_count", "request_body_sha256", "previous_batch_commitment_sha256"}
    item = _object(value, fields, "batch_schema_invalid")
    if item["batch_contract_version"] != "staging_event_batch_v1":
        raise ContractError("batch_contract_mismatch")
    _text(item["batch_id"], "batch_id_invalid")
    _text(item["attempt_id"], "attempt_id_invalid")
    _text(item["connector_instance_id"], "connector_instance_id_invalid")
    if item["candidate_registry_commitment_sha256"] != REGISTRY_COMMITMENT:
        raise ContractError("registry_commitment_mismatch")
    if item["event_contract_version"] != "shadow_event_v2":
        raise ContractError("event_contract_mismatch")
    events = _events(item["events"])
    if item["event_count"] != len(events):
        raise ContractError("event_count_mismatch")
    previous = item["previous_batch_commitment_sha256"]
    if previous is not None:
        _hash(previous, "previous_batch_commitment_invalid")
    expected = digest({key: val for key, val in item.items() if key != "request_body_sha256"})
    if _hash(item["request_body_sha256"], "request_body_hash_invalid") != expected:
        raise ContractError("request_body_hash_mismatch")
    return item


def validate_receiver_ack(value: Any, batch: dict[str, Any]) -> dict[str, Any]:
    fields = {"ack_contract_version", "batch_id", "attempt_id", "receiver_instance_id", "receiver_commit_id", "receiver_commit_sha256", "candidate_registry_commitment_sha256", "durable", "event_results", "ack_sha256"}
    item = _object(value, fields, "ack_schema_invalid")
    if item["ack_contract_version"] != "receiver_batch_ack_v1" or item["batch_id"] != batch["batch_id"] or item["attempt_id"] != batch["attempt_id"]:
        raise ContractError("ack_linkage_mismatch")
    if item["candidate_registry_commitment_sha256"] != REGISTRY_COMMITMENT or item["durable"] is not True:
        raise ContractError("ack_not_durable")
    results = item["event_results"]
    if not isinstance(results, list) or {r.get("event_id") for r in results} != {e["event_id"] for e in batch["events"]}:
        raise ContractError("partial_ack")
    allowed = {"accepted", "duplicate", "rejected_temporary", "rate_limited", "rejected_permanent"}
    if any(set(r) != {"event_id", "status", "error_code"} or r["status"] not in allowed for r in results):
        raise ContractError("unknown_ack_status")
    expected = digest({key: val for key, val in item.items() if key != "ack_sha256"})
    if _hash(item["ack_sha256"], "ack_hash_invalid") != expected:
        raise ContractError("ack_hash_mismatch")
    return item
