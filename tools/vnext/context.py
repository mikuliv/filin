"""Контекст, доверие, консервативное разрешение сущностей и время vNext."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from collections import Counter, defaultdict

from .contracts import ContractError, canonical_digest, validate_json_schema_instance
from .telemetry import assert_no_ground_truth_leakage, validate_entity, verify_digest, with_digest


TRUST_LEVELS = {"DECLARED_HIGH_TRUST", "OBSERVED", "INFERRED", "EXTERNAL", "UNKNOWN"}
RESOLUTION_STATES = {"EXACT", "STRONG", "WEAK", "UNRESOLVED"}
ORDERING_STATES = {"ON_TIME", "LATE_ACCEPTED", "TOO_LATE", "UNKNOWN_ORDER"}
NETWORK_CONTEXT_FEATURES = ("unique_destination_hosts", "unique_destination_ports", "unique_destination_services", "source_fan_out", "destination_fan_in", "host_fan_out", "port_fan_out", "service_fan_out", "connection_success_ratio", "failed_connection_ratio", "repeated_target_ratio", "new_target_ratio", "one_to_many_ratio", "many_to_one_ratio", "endpoint_stability", "target_diversity", "source_diversity", "cross_window_recurrence", "historical_target_overlap")


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ContractError("context timestamps require timezone")
    return parsed


def build_stable_entity(entity_type: str, attributes: dict[str, Any], *, namespace: str, provenance_scope: str, valid_from: str | None = None, valid_to: str | None = None) -> dict[str, Any]:
    identity = {"entity_type": entity_type, "attributes": attributes, "namespace": namespace, "provenance_scope": provenance_scope, "valid_from": valid_from, "valid_to": valid_to}
    base = {"schema_version": "entity_v1", "entity_type": entity_type, "attributes": attributes}
    result = dict(base, entity_id="ent_" + canonical_digest(identity))
    result["canonical_digest"] = canonical_digest(result)
    return validate_entity(result)


def resolve_entities(left: dict[str, Any], right: dict[str, Any], *, left_namespace: str, right_namespace: str, provenance_refs: list[str], shared_identifiers: list[str] | None = None, temporal_overlap: bool = True) -> dict[str, Any]:
    validate_entity(left); validate_entity(right)
    shared = sorted(set(shared_identifiers or []))
    reasons: list[str] = []
    if left["entity_id"] == right["entity_id"]:
        state = "EXACT"; reasons.append("canonical_identity_equal")
    elif left_namespace != right_namespace or left["entity_type"] != right["entity_type"]:
        state = "UNRESOLVED"; reasons.append("namespace_or_type_mismatch")
    elif shared and temporal_overlap:
        state = "STRONG"; reasons.append("shared_identifier_with_temporal_overlap")
    elif shared:
        state = "WEAK"; reasons.append("shared_identifier_without_temporal_overlap")
    else:
        state = "UNRESOLVED"; reasons.append("insufficient_identity_evidence")
    base = {"schema_version": "entity_resolution_v1", "left_entity_id": left["entity_id"], "right_entity_id": right["entity_id"], "state": state, "namespace": left_namespace if left_namespace == right_namespace else "cross_namespace", "provenance_refs": sorted(set(provenance_refs)), "reasons": reasons}
    result = with_digest(base, id_field="resolution_id", id_prefix="resolution")
    validate_json_schema_instance("entity_resolution_v1.schema.json", result); verify_digest(result)
    return result


def build_context_fact(subject_entity_id: str, fact_type: str, value: Any, *, source: str, provenance: dict[str, Any], trust: str, first_seen: str, last_seen: str, validity: dict[str, str] | None = None) -> dict[str, Any]:
    if trust not in TRUST_LEVELS or _time(first_seen) > _time(last_seen):
        raise ContractError("invalid context trust or time range")
    if validity and _time(validity["from"]) > _time(validity["until"]):
        raise ContractError("invalid context validity interval")
    base = {"schema_version": "context_fact_v1", "subject_entity_id": subject_entity_id, "fact_type": fact_type, "value": value, "source": source, "provenance": provenance, "trust": trust, "first_seen": first_seen, "last_seen": last_seen, "validity": validity}
    assert_no_ground_truth_leakage(base)
    result = with_digest(base, id_field="fact_id", id_prefix="ctx")
    validate_json_schema_instance("context_fact_v1.schema.json", result); verify_digest(result)
    return result


def build_context_profile(facts: list[dict[str, Any]], as_of: str) -> dict[str, Any]:
    for fact in facts:
        validate_json_schema_instance("context_fact_v1.schema.json", fact); verify_digest(fact)
    ordered = sorted(facts, key=lambda row: row["fact_id"])
    base = {"schema_version": "context_profile_v1", "as_of": as_of, "facts": ordered}
    result = with_digest(base, id_field="profile_id", id_prefix="context")
    validate_json_schema_instance("context_profile_v1.schema.json", result); verify_digest(result); assert_no_ground_truth_leakage(result)
    return result


def context_fact_state(fact: dict[str, Any], as_of: str, *, stale_after_seconds: float) -> str:
    now = _time(as_of)
    validity = fact.get("validity")
    if validity and not (_time(validity["from"]) <= now <= _time(validity["until"])):
        return "STALE"
    if (now - _time(fact["last_seen"])).total_seconds() > stale_after_seconds:
        return "STALE"
    return "ACTIVE"


def build_window_policy(short_seconds: float = 30, behavior_seconds: float = 300, context_seconds: float = 3600, allowed_lateness_seconds: float = 10) -> dict[str, Any]:
    if not 0 < short_seconds <= behavior_seconds <= context_seconds:
        raise ContractError("window horizons must be positive and ordered")
    base = {"schema_version": "multi_window_policy_v1", "policy_id": "filin_vnext_multi_window_v1", "horizons": {"short": short_seconds, "behavior": behavior_seconds, "context": context_seconds}, "allowed_lateness_seconds": allowed_lateness_seconds}
    result = with_digest(base); validate_json_schema_instance("multi_window_policy_v1.schema.json", result); verify_digest(result)
    return result


def ordering_status(event_time: str | None, ingest_time: str | None, watermark: str | None, allowed_lateness_seconds: float) -> str:
    if not event_time or not ingest_time or not watermark:
        return "UNKNOWN_ORDER"
    event, ingest, mark = _time(event_time), _time(ingest_time), _time(watermark)
    if event >= mark:
        return "ON_TIME"
    if (mark - event).total_seconds() <= allowed_lateness_seconds and ingest >= event:
        return "LATE_ACCEPTED"
    return "TOO_LATE"


def network_context_feature_values(events: list[dict[str, Any]], historical_events: list[dict[str, Any]] | None = None) -> dict[str, float]:
    flows = [row for row in events if row["event_type"] == "network.flow"]
    history = [row for row in (historical_events or []) if row["event_type"] == "network.flow"]
    if not flows:
        raise ContractError("network context requires network.flow telemetry")
    def source(row: dict[str, Any]) -> str: return row["payload"]["source"]["ip"]
    def destination(row: dict[str, Any]) -> str: return row["payload"]["destination"]["ip"]
    def port(row: dict[str, Any]) -> int: return int(row["payload"]["destination"].get("port", 0))
    def target(row: dict[str, Any]) -> tuple[str, int]: return destination(row), port(row)
    sources = Counter(source(row) for row in flows); destinations = Counter(destination(row) for row in flows); ports = Counter(port(row) for row in flows)
    targets = Counter(target(row) for row in flows); services = Counter((row["payload"].get("application_protocol", "unknown"), port(row)) for row in flows)
    by_source: dict[str, set[tuple[str, int]]] = defaultdict(set); by_destination: dict[str, set[str]] = defaultdict(set)
    for row in flows:
        by_source[source(row)].add(target(row)); by_destination[destination(row)].add(source(row))
    historical_targets = {target(row) for row in history}; current_targets = set(targets); overlap = current_targets & historical_targets
    successes = sum(row["action"]["outcome"] == "success" for row in flows); total = len(flows)
    return {
        "unique_destination_hosts": float(len(destinations)), "unique_destination_ports": float(len(ports)), "unique_destination_services": float(len(services)),
        "source_fan_out": sum(map(len, by_source.values()))/len(by_source), "destination_fan_in": sum(map(len, by_destination.values()))/len(by_destination),
        "host_fan_out": float(len(destinations)), "port_fan_out": float(len(ports)), "service_fan_out": float(len(services)),
        "connection_success_ratio": successes/total, "failed_connection_ratio": (total-successes)/total,
        "repeated_target_ratio": sum(count-1 for count in targets.values())/total, "new_target_ratio": len(current_targets-historical_targets)/len(current_targets),
        "one_to_many_ratio": sum(len(items)>1 for items in by_source.values())/len(by_source), "many_to_one_ratio": sum(len(items)>1 for items in by_destination.values())/len(by_destination),
        "endpoint_stability": max(targets.values())/total, "target_diversity": len(current_targets)/total, "source_diversity": len(sources)/total,
        "cross_window_recurrence": len(overlap)/len(current_targets), "historical_target_overlap": len(overlap)/len(current_targets | historical_targets) if current_targets | historical_targets else 0.0,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
