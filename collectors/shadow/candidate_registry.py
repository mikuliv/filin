from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from .canonical import canonical_bytes

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).parent / "contracts" / "shadow_event_v2.schema.json"
REGISTRY_PATH = Path(__file__).parent / "contracts" / "candidate_registry_v1.json"
COMMITMENT_PATH = Path(__file__).parent / "contracts" / "candidate_registry_v1.commitment.json"
V2_VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
MAX_EVENT_BYTES = 8192

ERROR_CODES = (
    "invalid_json", "event_too_large", "schema_validation_failed", "unsupported_event_contract",
    "registry_commitment_mismatch", "candidate_not_registered", "candidate_inactive",
    "candidate_not_allowed_for_campaign", "candidate_artifact_hash_mismatch",
    "candidate_manifest_hash_mismatch", "feature_contract_mismatch", "preprocessing_hash_mismatch",
    "calibration_hash_mismatch", "conformal_hash_mismatch", "state_policy_hash_mismatch",
    "runtime_compatibility_mismatch", "prediction_linkage_mismatch", "privacy_validation_failed",
    "duplicate_event_identity", "idempotency_collision",
)

VALIDATION_ORDER = (
    "parse_json", "event_size", "v2_schema", "contract_version", "registry_commitment",
    "candidate_lookup", "candidate_status", "campaign_allowlist", "artifact_hash", "manifest_hash",
    "feature_contract", "preprocessing_hash", "calibration_hash", "conformal_hash", "state_policy_hash",
    "runtime_compatibility", "prediction_linkage", "privacy", "canonical_serialization", "event_hash", "durable_spool",
)

FORBIDDEN_KEYS = {"raw_pcap", "pcap", "http_body", "authentication_data", "password", "token", "cookie", "authorization", "username", "email", "ip_address", "mac_address", "hostname", "label", "true_class", "features", "feature_vector", "scenario_class", "filesystem_path"}


class ContractValidationError(ValueError):
    def __init__(self, code: str):
        if code not in ERROR_CODES:
            raise ValueError("unknown_validation_error_code")
        self.code = code
        super().__init__(code)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_registry() -> tuple[dict, dict]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8")), json.loads(COMMITMENT_PATH.read_text(encoding="utf-8"))


def validate_registry_artifacts() -> bool:
    registry, commitment = load_registry()
    canonical = json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if sha256_bytes(REGISTRY_PATH.read_bytes()) != commitment["candidate_registry_sha256"]:
        raise ContractValidationError("registry_commitment_mismatch")
    if sha256_bytes(canonical) != commitment["candidate_registry_commitment_sha256"]:
        raise ContractValidationError("registry_commitment_mismatch")
    ids = [item["candidate_id"] for item in registry["candidates"]]
    if len(ids) != len(set(ids)):
        raise ContractValidationError("candidate_not_registered")
    return True


def _privacy_findings(value: object) -> list[str]:
    import re
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    findings: list[str] = []
    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if key.casefold() in FORBIDDEN_KEYS:
                    findings.append("forbidden_key")
                visit(nested)
        elif isinstance(item, list):
            for nested in item: visit(nested)
    visit(value)
    patterns = [r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", r"bearer\s+\S+", r"[A-Za-z]:\\Users\\", r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b"]
    findings.extend("forbidden_pattern" for pattern in patterns if re.search(pattern, text, re.I))
    return findings


def validate_v2(raw: bytes | str | dict, *, allowlist: set[str] | None = None, prediction_index: dict[str, str] | None = None, seen_events: dict[str, str] | None = None, seen_idempotency: dict[str, str] | None = None) -> dict:
    if isinstance(raw, dict):
        event = raw
        encoded = canonical_bytes(event)
    else:
        encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
        try: event = json.loads(encoded)
        except (ValueError, TypeError): raise ContractValidationError("invalid_json")
    if len(encoded) > MAX_EVENT_BYTES: raise ContractValidationError("event_too_large")
    errors = sorted(V2_VALIDATOR.iter_errors(event), key=lambda error: list(error.path))
    if errors: raise ContractValidationError("schema_validation_failed")
    if event["event_contract_version"] != "shadow_event_v2": raise ContractValidationError("unsupported_event_contract")
    validate_registry_artifacts()
    registry, commitment = load_registry()
    if event["candidate_ref"]["registry_commitment_sha256"] != commitment["candidate_registry_commitment_sha256"]: raise ContractValidationError("registry_commitment_mismatch")
    entries = {item["candidate_id"]: item for item in registry["candidates"]}
    candidate = entries.get(event["candidate_ref"]["candidate_id"])
    if candidate is None: raise ContractValidationError("candidate_not_registered")
    if candidate["revoked"] or candidate["status"] not in {"active_for_local_runtime_trial", "historical"}: raise ContractValidationError("candidate_inactive")
    allowed = allowlist if allowlist is not None else {"v03154:65a3dd912d845bc1"}
    if candidate["candidate_id"] not in allowed: raise ContractValidationError("candidate_not_allowed_for_campaign")
    ref = event["candidate_ref"]
    checks = (("artifact_sha256", "candidate_artifact_hash_mismatch"), ("manifest_sha256", "candidate_manifest_hash_mismatch"), ("feature_contract_sha256", "feature_contract_mismatch"), ("preprocessing_sha256", "preprocessing_hash_mismatch"), ("calibration_sha256", "calibration_hash_mismatch"), ("conformal_sha256", "conformal_hash_mismatch"), ("state_policy_sha256", "state_policy_hash_mismatch"))
    for key, code in checks:
        if ref[key] != candidate[key]: raise ContractValidationError(code)
    if ref["feature_contract_id"] != candidate["feature_contract_id"]: raise ContractValidationError("feature_contract_mismatch")
    if "shadow_event_v2" not in candidate["supported_event_contract_versions"] or event["runtime_ref"]["runtime_contract_version"] != "passive_runtime_v031551": raise ContractValidationError("runtime_compatibility_mismatch")
    if prediction_index is not None and prediction_index.get(event["prediction_ref"]["prediction_id"]) != event["prediction_ref"]["prediction_sha256"]: raise ContractValidationError("prediction_linkage_mismatch")
    if _privacy_findings(event): raise ContractValidationError("privacy_validation_failed")
    event_hash = sha256_bytes(canonical_bytes(event))
    if seen_events is not None and event["event_id"] in seen_events:
        if seen_events[event["event_id"]] != event_hash: raise ContractValidationError("duplicate_event_identity")
    if seen_idempotency is not None and event["idempotency_key"] in seen_idempotency:
        if seen_idempotency[event["idempotency_key"]] != event["event_id"]: raise ContractValidationError("idempotency_collision")
    return event
