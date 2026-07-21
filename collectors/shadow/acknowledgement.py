from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ACK_PROTOCOL = "shadow_ack_v1"
ACK_SCHEMA = "shadow_ack_schema_v1"
SUCCESS = {"accepted", "duplicate"}
RETRYABLE = {"rejected_temporary", "rate_limited"}
PERMANENT = {"rejected_permanent"}
ERROR_CLASS_BY_STATUS = {
    "accepted": {"none"},
    "duplicate": {"none"},
    "rejected_temporary": {"timeout", "sink_unavailable", "connection_reset", "slow_consumer"},
    "rate_limited": {"rate_limit"},
    "rejected_permanent": {"schema_rejection", "invalid_contract", "authentication", "authorization", "unsupported_schema", "policy_rejection"},
}


@dataclass(frozen=True)
class AckDecision:
    outcome: str
    status: str
    error_class: str
    retry_after_ms: int | None


class AckContractError(ValueError):
    pass


def validate_ack(value: Any, event: dict) -> AckDecision:
    if not isinstance(value, dict):
        raise AckContractError("malformed_ack:not_object")
    required = {"protocol_version", "schema_version", "idempotency_key", "status", "error_class", "retryable"}
    if set(value) - (required | {"sink_sequence", "sink_timestamp", "retry_after_ms"}) or not required.issubset(value):
        raise AckContractError("malformed_ack:fields")
    if value["protocol_version"] != ACK_PROTOCOL or value["schema_version"] != ACK_SCHEMA:
        raise AckContractError("malformed_ack:version")
    if value["idempotency_key"] != event["idempotency_key"]:
        raise AckContractError("malformed_ack:identity")
    status = value["status"]
    if status not in SUCCESS | RETRYABLE | PERMANENT:
        raise AckContractError("unknown_ack_status")
    error_class = value["error_class"]
    if error_class not in ERROR_CLASS_BY_STATUS[status]:
        raise AckContractError("malformed_ack:status_error_combination")
    expected_retryable = status in RETRYABLE
    if value["retryable"] is not expected_retryable:
        raise AckContractError("malformed_ack:retryable_mismatch")
    retry_after = value.get("retry_after_ms")
    if retry_after is not None and (not isinstance(retry_after, int) or retry_after < 0 or retry_after > 60_000):
        raise AckContractError("malformed_ack:retry_after")
    outcome = "success" if status in SUCCESS else "retryable_failure" if status in RETRYABLE else "permanent_rejection"
    return AckDecision(outcome, status, error_class, retry_after)


def make_ack(event: dict, status: str = "accepted", error_class: str = "none", *, sequence: int = 0, retry_after_ms: int | None = None) -> dict:
    value = {
        "protocol_version": ACK_PROTOCOL,
        "schema_version": ACK_SCHEMA,
        "idempotency_key": event["idempotency_key"],
        "status": status,
        "error_class": error_class,
        "retryable": status in RETRYABLE,
        "sink_sequence": sequence,
    }
    if retry_after_ms is not None:
        value["retry_after_ms"] = retry_after_ms
    return value
