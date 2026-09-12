"""Версионированные признаки vNext, строящиеся только из пакета наблюдений."""
from __future__ import annotations

import math
import statistics
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .contracts import CONTRACT_ROOT, ContractError, canonical_digest, load_json, validate_json_schema_instance
from .telemetry import assert_no_ground_truth_leakage, verify_digest, with_digest
from .context import NETWORK_CONTEXT_FEATURES, network_context_feature_values
from .graph import GRAPH_FEATURES, graph_feature_values


FEATURE_STATUS = {"AVAILABLE", "UNAVAILABLE_TELEMETRY", "INSUFFICIENT_DATA", "UNSUPPORTED", "INVALID_INPUT"}
TEMPORAL_FEATURES = ("inter_arrival_count", "mean_interval_ms", "median_interval_ms", "interval_stddev_ms", "interval_cv", "min_interval_ms", "max_interval_ms", "burstiness", "event_rate", "connection_rate", "active_window_duration_ms", "periodicity_score", "jitter_estimate")
AUTH_FEATURES = ("attempt_count", "success_count", "failure_count", "failure_ratio", "unique_accounts", "mean_attempts_per_account", "max_account_concentration", "unique_sources", "source_concentration", "unique_targets", "temporal_spread_ms", "retry_interval_mean_ms", "account_fanout", "source_fanout")
HTTP_FEATURES = ("request_count", "get_share", "post_share", "unique_paths", "path_fanout", "status_2xx_share", "status_4xx_share", "status_5xx_share", "mean_request_bytes", "mean_response_bytes", "repeated_path_ratio", "mean_path_depth", "request_rate", "error_ratio", "unique_hosts", "user_agent_diversity", "session_concentration")
DNS_FEATURES = ("query_count", "unique_domains", "mean_subdomain_depth", "mean_query_length", "mean_label_entropy", "query_type_diversity", "nxdomain_ratio", "unique_labels", "repetition_ratio", "query_rate", "resolver_diversity", "mean_answer_count")

PROVIDERS = {
    "temporal_v1": ("temporal_v1_provider", "filin://vnext/temporal_feature_group_v1", ("network.flow", "http.request", "auth.attempt", "dns.query"), TEMPORAL_FEATURES),
    "authentication_v1": ("authentication_v1_provider", "filin://vnext/authentication_feature_group_v1", ("auth.attempt",), AUTH_FEATURES),
    "http_behavior_v1": ("http_behavior_v1_provider", "filin://vnext/http_behavior_feature_group_v1", ("http.request",), HTTP_FEATURES),
    "dns_v1": ("dns_v1_provider", "filin://vnext/dns_feature_group_v1", ("dns.query",), DNS_FEATURES),
    "legacy_network_v2": ("legacy_network_features_v2_provider", "filin://vnext/legacy_network_v2", ("network.flow", "dns.query", "http.request"), (),),
    "network_context_v1": ("network_context_v1_provider", "filin://vnext/network_context_feature_group_v1", ("network.flow",), NETWORK_CONTEXT_FEATURES),
    "interaction_graph_v1": ("interaction_graph_v1_provider", "filin://vnext/interaction_graph_feature_group_v1", ("network.flow",), GRAPH_FEATURES),
}


def _schema_digest(group_id: str) -> str:
    if group_id == "legacy_network_v2":
        return load_json(CONTRACT_ROOT / "legacy_network_features_v2_compatibility.json")["feature_contract"]["contract_sha256"]
    filename = {"temporal_v1": "temporal_feature_group_v1.schema.json", "authentication_v1": "authentication_feature_group_v1.schema.json", "http_behavior_v1": "http_behavior_feature_group_v1.schema.json", "dns_v1": "dns_feature_group_v1.schema.json", "network_context_v1": "network_context_feature_group_v1.schema.json", "interaction_graph_v1": "interaction_graph_feature_group_v1.schema.json"}[group_id]
    return canonical_digest(load_json(CONTRACT_ROOT / filename))


def _time(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _group(group_id: str, observation: dict[str, Any], events: list[dict[str, Any]], names: tuple[str, ...], values: dict[str, float | None], status: str = "AVAILABLE", missing: list[dict[str, str]] | None = None) -> dict[str, Any]:
    provider_id, schema_id, required, _ = PROVIDERS[group_id]
    event_refs = [event["event_id"] for event in events]
    value = {"schema_version": "feature_group_v1", "schema_id": schema_id, "schema_digest": _schema_digest(group_id), "group_id": group_id, "provider_id": provider_id, "provider_version": "1.0.0", "status": status,
             "required_telemetry": list(required), "telemetry_requirement_mode": "any" if group_id == "temporal_v1" else "all", "ordered_feature_names": list(names), "values": {name: values[name] for name in names if name in values}, "missing_data": missing or [],
             "provenance": {"observation_bundle_id": observation["bundle_id"], "observation_digest": observation["canonical_digest"], "event_refs": event_refs, "algorithm": f"{provider_id}:1.0.0"}}
    result = with_digest(value); validate_feature_group(result); return result


def _unavailable(group_id: str, observation: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    names = PROVIDERS[group_id][3]
    if group_id == "legacy_network_v2":
        names = tuple(load_json(CONTRACT_ROOT / "legacy_network_features_v2_compatibility.json")["feature_contract"]["ordered_feature_names"])
    missing = [{"feature_name": name, "status": status, "reason": reason} for name in names]
    return _group(group_id, observation, [], names, {}, status, missing)


def temporal_features(observation: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    # Производные flow/http записи одного запроса имеют одинаковое время; выбираем
    # наиболее содержательный тип, чтобы не создавать искусственные нулевые интервалы.
    preferred = next((kind for kind in ("auth.attempt", "http.request", "dns.query", "network.flow") if any(event["event_type"] == kind for event in events)), None)
    relevant = sorted([event for event in events if event["event_type"] == preferred], key=lambda event: (_time(event["temporal"]["event_timestamp"]), event["event_id"]))
    if not relevant: return _unavailable("temporal_v1", observation, "UNAVAILABLE_TELEMETRY", "Нет поддерживаемых событий.")
    times = [_time(event["temporal"]["event_timestamp"]) for event in relevant]
    intervals = [(right - left) * 1000 for left, right in zip(times, times[1:])]
    duration_ms = max(0.0, (times[-1] - times[0]) * 1000); duration_s = max(duration_ms / 1000, 1e-9)
    mean = _mean(intervals); std = statistics.pstdev(intervals) if len(intervals) > 1 else 0.0; median = statistics.median(intervals) if intervals else 0.0
    connections = sum(event["event_type"] in {"network.flow", "network.connection"} for event in relevant)
    values = {"inter_arrival_count": float(len(intervals)), "mean_interval_ms": mean, "median_interval_ms": median, "interval_stddev_ms": std, "interval_cv": _ratio(std, mean), "min_interval_ms": min(intervals, default=0.0), "max_interval_ms": max(intervals, default=0.0), "burstiness": _ratio(std - mean, std + mean), "event_rate": len(relevant) / duration_s, "connection_rate": connections / duration_s, "active_window_duration_ms": duration_ms, "periodicity_score": max(0.0, 1.0 - min(1.0, _ratio(std, mean))), "jitter_estimate": _ratio(_mean([abs(item - median) for item in intervals]), mean)}
    missing = [] if intervals else [{"feature_name": name, "status": "INSUFFICIENT_DATA", "reason": "Для интервалов требуется минимум два события."} for name in TEMPORAL_FEATURES[1:9] + TEMPORAL_FEATURES[11:]]
    return _group("temporal_v1", observation, relevant, TEMPORAL_FEATURES, values, "AVAILABLE" if intervals else "INSUFFICIENT_DATA", missing)


def authentication_features(observation: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [event for event in events if event["event_type"] == "auth.attempt"]
    if not rows: return _unavailable("authentication_v1", observation, "UNAVAILABLE_TELEMETRY", "Нет событий auth.attempt.")
    accounts = Counter(row["payload"]["account_entity_id"] for row in rows)
    sources = Counter(next((ref["entity_id"] for ref in row["entity_refs"] if ref["role"] == "source"), "unattributed") for row in rows)
    targets = {row["payload"].get("target_service_entity_id", "unattributed") for row in rows}
    times = sorted(_time(row["temporal"]["event_timestamp"]) for row in rows); retry = [(b-a)*1000 for a,b in zip(times,times[1:])]
    failures = sum(not row["payload"]["success"] for row in rows); total = len(rows)
    values = {"attempt_count": float(total), "success_count": float(total-failures), "failure_count": float(failures), "failure_ratio": failures/total, "unique_accounts": float(len(accounts)), "mean_attempts_per_account": total/len(accounts), "max_account_concentration": max(accounts.values())/total, "unique_sources": float(len(sources)), "source_concentration": max(sources.values())/total, "unique_targets": float(len(targets)), "temporal_spread_ms": (times[-1]-times[0])*1000, "retry_interval_mean_ms": _mean(retry), "account_fanout": float(len(accounts)), "source_fanout": float(len(sources))}
    return _group("authentication_v1", observation, rows, AUTH_FEATURES, values)


def http_features(observation: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [event for event in events if event["event_type"] == "http.request"]
    if not rows: return _unavailable("http_behavior_v1", observation, "UNAVAILABLE_TELEMETRY", "Нет событий http.request.")
    total = len(rows); methods = Counter(row["payload"]["method"].upper() for row in rows); paths = Counter(row["payload"].get("path", "") for row in rows); statuses = [row["payload"].get("status_code", 0) for row in rows]
    hosts = {row["payload"].get("host", "") for row in rows}; times = sorted(_time(row["temporal"]["event_timestamp"]) for row in rows); duration = max(times[-1]-times[0], 1e-9)
    values = {"request_count": float(total), "get_share": _ratio(methods["GET"], total), "post_share": _ratio(methods["POST"], total), "unique_paths": float(len(paths)), "path_fanout": _ratio(len(paths), total), "status_2xx_share": _ratio(sum(200 <= x < 300 for x in statuses), total), "status_4xx_share": _ratio(sum(400 <= x < 500 for x in statuses), total), "status_5xx_share": _ratio(sum(500 <= x < 600 for x in statuses), total), "mean_request_bytes": _mean([row["payload"].get("request_bytes", 0) for row in rows]), "mean_response_bytes": _mean([row["payload"].get("response_bytes", 0) for row in rows]), "repeated_path_ratio": _ratio(sum(count-1 for count in paths.values()), total), "mean_path_depth": _mean([len([part for part in path.split("/") if part]) for path in paths.elements()]), "request_rate": total/duration, "error_ratio": _ratio(sum(x >= 400 for x in statuses), total), "unique_hosts": float(len(hosts)), "session_concentration": 1.0}
    missing = [{"feature_name": "user_agent_diversity", "status": "UNSUPPORTED", "reason": "Нормализованный HTTP-контракт не содержит user-agent."}]
    return _group("http_behavior_v1", observation, rows, HTTP_FEATURES, values, "AVAILABLE", missing)


def _entropy(label: str) -> float:
    counts = Counter(label); total = len(label)
    return -sum((count/total) * math.log2(count/total) for count in counts.values()) if total else 0.0


def dns_features(observation: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [event for event in events if event["event_type"] == "dns.query"]
    if not rows: return _unavailable("dns_v1", observation, "UNAVAILABLE_TELEMETRY", "Нет событий dns.query.")
    names = [row["payload"]["question_name"].lower().rstrip(".") for row in rows]; total = len(rows); counts = Counter(names); labels = [part for name in names for part in name.split(".")]
    types = {row["payload"].get("question_type", "UNKNOWN") for row in rows}; times = sorted(_time(row["temporal"]["event_timestamp"]) for row in rows); duration = max(times[-1]-times[0], 1e-9)
    resolvers = {next((ref["entity_id"] for ref in row["entity_refs"] if ref["role"] == "destination"), "unattributed") for row in rows}
    values = {"query_count": float(total), "unique_domains": float(len(counts)), "mean_subdomain_depth": _mean([max(0, len(name.split("."))-2) for name in names]), "mean_query_length": _mean([len(name) for name in names]), "mean_label_entropy": _mean([_entropy(label) for label in labels]), "query_type_diversity": float(len(types)), "nxdomain_ratio": _ratio(sum(row["payload"].get("response_code") == "NXDOMAIN" for row in rows), total), "unique_labels": float(len(set(labels))), "repetition_ratio": _ratio(sum(count-1 for count in counts.values()), total), "query_rate": total/duration, "resolver_diversity": float(len(resolvers)), "mean_answer_count": _mean([len(row["payload"].get("answers", [])) for row in rows])}
    return _group("dns_v1", observation, rows, DNS_FEATURES, values)


def legacy_network_group(observation: dict[str, Any], events: list[dict[str, Any]], values: list[float] | None = None) -> dict[str, Any]:
    contract = load_json(CONTRACT_ROOT / "legacy_network_features_v2_compatibility.json"); names = tuple(contract["feature_contract"]["ordered_feature_names"])
    if values is None: return _unavailable("legacy_network_v2", observation, "UNSUPPORTED", "Для точного адаптера требуются исходные каталоги Zeek, а не реконструкция из normalized events.")
    if len(values) != 51: raise ContractError("legacy feature vector must contain exactly 51 values")
    return _group("legacy_network_v2", observation, events, names, dict(zip(names, map(float, values))))


def network_context_group(observation: dict[str, Any], events: list[dict[str, Any]], historical_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = [row for row in events if row["event_type"] == "network.flow"]
    if not rows: return _unavailable("network_context_v1", observation, "UNAVAILABLE_TELEMETRY", "Нет событий network.flow.")
    return _group("network_context_v1", observation, rows, NETWORK_CONTEXT_FEATURES, network_context_feature_values(events, historical_events))


def interaction_graph_group(observation: dict[str, Any], events: list[dict[str, Any]], graph: dict[str, Any] | None = None, previous_graph: dict[str, Any] | None = None) -> dict[str, Any]:
    if graph is None: return _unavailable("interaction_graph_v1", observation, "UNSUPPORTED", "Граф взаимодействий не передан.")
    return _group("interaction_graph_v1", observation, events, GRAPH_FEATURES, graph_feature_values(graph, previous_graph))


def validate_feature_group(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("feature_group_v1.schema.json", value); assert_no_ground_truth_leakage(value); verify_digest(value)
    specific = {"temporal_v1": "temporal_feature_group_v1.schema.json", "authentication_v1": "authentication_feature_group_v1.schema.json", "http_behavior_v1": "http_behavior_feature_group_v1.schema.json", "dns_v1": "dns_feature_group_v1.schema.json", "network_context_v1": "network_context_feature_group_v1.schema.json", "interaction_graph_v1": "interaction_graph_feature_group_v1.schema.json"}.get(value["group_id"])
    if specific: validate_json_schema_instance(specific, value)
    names = tuple(value["ordered_feature_names"]); expected = PROVIDERS[value["group_id"]][3]
    if value["group_id"] == "legacy_network_v2": expected = tuple(load_json(CONTRACT_ROOT / "legacy_network_features_v2_compatibility.json")["feature_contract"]["ordered_feature_names"])
    if names != expected or any(key not in names for key in value["values"]): raise ContractError("feature order or value name mismatch")
    if value["status"] not in FEATURE_STATUS: raise ContractError("unknown feature status")
    return value


def load_feature_provider_registry() -> dict[str, Any]:
    return load_json(CONTRACT_ROOT / "feature_provider_registry_v1.json")


def validate_feature_provider_registry(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("feature_provider_registry_v1.schema.json", value); verify_digest(value)
    ids = [row["provider_id"] for row in value["providers"]]
    if len(ids) != len(set(ids)): raise ContractError("duplicate feature provider")
    for row in value["providers"]:
        expected = PROVIDERS[row["group_id"]][3]
        if row["group_id"] == "legacy_network_v2": expected = tuple(load_json(CONTRACT_ROOT / "legacy_network_features_v2_compatibility.json")["feature_contract"]["ordered_feature_names"])
        if tuple(row["ordered_feature_names"]) != expected: raise ContractError("provider feature order mismatch")
        if row["schema_digest"] != _schema_digest(row["group_id"]): raise ContractError("provider schema digest mismatch")
    return value


def validate_feature_bundle(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("feature_bundle_v1.schema.json", value); assert_no_ground_truth_leakage(value); verify_digest(value)
    groups = value["groups"]
    if len({group["group_id"] for group in groups}) != len(groups): raise ContractError("duplicate feature group")
    for group in groups: validate_feature_group(group)
    return value


def build_feature_bundle(observation: dict[str, Any], events: list[dict[str, Any]], *, legacy_values: list[float] | None = None, historical_events: list[dict[str, Any]] | None = None, interaction_graph: dict[str, Any] | None = None, previous_graph: dict[str, Any] | None = None) -> dict[str, Any]:
    assert_no_ground_truth_leakage(observation); assert_no_ground_truth_leakage(events)
    groups = [temporal_features(observation, events), authentication_features(observation, events), http_features(observation, events), dns_features(observation, events), legacy_network_group(observation, events, legacy_values), network_context_group(observation, events, historical_events), interaction_graph_group(observation, events, interaction_graph, previous_graph)]
    registry = validate_feature_provider_registry(load_feature_provider_registry())
    missing = [{"group_id": group["group_id"], "status": group["status"], "reason": group["missing_data"][0]["reason"] if group["missing_data"] else "Группа недоступна."} for group in groups if group["status"] != "AVAILABLE"]
    base = {"schema_version": "feature_bundle_v1", "observation_ref": {"bundle_id": observation["bundle_id"], "canonical_digest": observation["canonical_digest"]}, "raw_evidence_refs": deepcopy(observation["raw_evidence_refs"]), "groups": groups, "missing_groups": missing, "provider_registry_digest": registry["canonical_digest"], "ground_truth_used": False}
    result = with_digest(base, id_field="feature_bundle_id", id_prefix="feature_bundle"); return validate_feature_bundle(result)


def build_feature_provider_registry() -> dict[str, Any]:
    families = {"temporal_v1": ["malicious.command_and_control", "benign.operations.monitoring", "benign.automation"], "authentication_v1": ["malicious.credential_abuse", "benign.authentication"], "http_behavior_v1": ["malicious.reconnaissance", "malicious.command_and_control", "benign.automation"], "dns_v1": ["malicious.command_and_control", "malicious.protocol_abuse", "benign.dns"], "legacy_network_v2": ["malicious", "benign"], "network_context_v1": ["malicious.reconnaissance", "malicious.command_and_control", "benign.operations.monitoring"], "interaction_graph_v1": ["malicious.reconnaissance", "malicious.credential_abuse", "malicious.command_and_control", "benign.operations.monitoring"]}
    rows = []
    for group_id, (provider_id, schema_id, required, names) in PROVIDERS.items():
        if group_id == "legacy_network_v2": names = tuple(load_json(CONTRACT_ROOT / "legacy_network_features_v2_compatibility.json")["feature_contract"]["ordered_feature_names"])
        rows.append({"provider_id": provider_id, "group_id": group_id, "schema_id": schema_id, "schema_digest": _schema_digest(group_id), "version": "2.0.0" if group_id == "legacy_network_v2" else "1.0.0", "required_telemetry": list(required), "telemetry_requirement_mode": "any" if group_id == "temporal_v1" else "all", "supported_event_types": list(required), "supported_behavior_families": families[group_id], "ordered_feature_names": list(names), "missing_data_policy": "explicit_typed_status", "deterministic": True, "maturity": "frozen" if group_id == "legacy_network_v2" else "implemented"})
    return with_digest({"schema_version": "feature_provider_registry_v1", "registry_id": "filin_vnext_feature_providers_v1", "status": "implemented", "providers": rows})
