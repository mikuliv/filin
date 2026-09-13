"""Версионированный временной граф взаимодействий Filin vNext."""
from __future__ import annotations

import math
from copy import deepcopy
from collections import Counter, defaultdict
from typing import Any

from .contracts import ContractError, canonical_digest, validate_json_schema_instance
from .telemetry import assert_no_ground_truth_leakage, verify_digest, with_digest


NODE_TYPES = {"entity", "observation", "detection_result", "correlation_result", "incident_candidate"}
EDGE_TYPES = {"CONNECTED_TO", "AUTHENTICATED_TO", "REQUESTED", "QUERIED", "ACCESSED_SERVICE", "OBSERVED_IN", "PRECEDES", "SUPPORTED_BY", "CONTRADICTS", "ASSOCIATED_WITH"}
GRAPH_FEATURES = ("out_degree", "in_degree", "weighted_degree", "unique_neighbor_count", "edge_type_distribution", "repeated_edge_ratio", "new_neighbor_ratio", "degree_change", "local_density", "temporal_edge_recurrence", "service_concentration", "account_host_fan_out", "host_account_fan_in")


def _ephemeral_entity_id(kind: str, value: str) -> str:
    """Создаёт локальную проекцию графа, а не каноническую сущность."""
    return "eph_" + canonical_digest({"kind": kind, "value": value})


def _entity_node(node_id: str, entity_type: str, identity_scope: str) -> dict[str, Any]:
    return {"node_id": node_id, "node_type": "entity", "entity_type": entity_type, "canonical_ref": None, "identity_scope": identity_scope}


def _add_edge(edges: dict[tuple[str, str, str, str], dict[str, Any]], source: str, target: str, edge_type: str, timestamp: str, observation_id: str, direction: str = "directed") -> None:
    if edge_type not in EDGE_TYPES:
        raise ContractError("unsupported graph edge type")
    key = (source, target, edge_type, direction)
    if key not in edges:
        edges[key] = {"source": source, "target": target, "edge_type": edge_type, "first_seen": timestamp, "last_seen": timestamp, "count": 0, "observation_ids": [], "direction": direction}
    edge = edges[key]; edge["count"] += 1
    edge["first_seen"] = min(edge["first_seen"], timestamp); edge["last_seen"] = max(edge["last_seen"], timestamp)
    edge["observation_ids"] = sorted(set(edge["observation_ids"] + [observation_id]))


def build_interaction_graph(observations: list[dict[str, Any]], event_windows: list[list[dict[str, Any]]], detections: list[dict[str, Any]] | None = None, *, docker_evidence_refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if len(observations) != len(event_windows) or not observations:
        raise ContractError("graph requires aligned observation and event windows")
    assert_no_ground_truth_leakage(observations); assert_no_ground_truth_leakage(event_windows)
    nodes: dict[str, dict[str, Any]] = {}; edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for index, (observation, events) in enumerate(zip(observations, event_windows)):
        oid = observation["bundle_id"]
        nodes[oid] = {"node_id": oid, "node_type": "observation", "entity_type": None, "canonical_ref": observation["canonical_digest"], "identity_scope": "artifact"}
        if index:
            previous = observations[index - 1]
            _add_edge(edges, previous["bundle_id"], oid, "PRECEDES", observation["window"]["start"], oid)
        for event in events:
            timestamp = event["temporal"]["event_timestamp"]
            for ref in event["entity_refs"]:
                nodes.setdefault(ref["entity_id"], _entity_node(ref["entity_id"], ref["entity_type"], "external_entity_reference"))
                _add_edge(edges, ref["entity_id"], oid, "OBSERVED_IN", timestamp, oid)
            refs = {ref["role"]: ref["entity_id"] for ref in event["entity_refs"]}
            source, destination = refs.get("source"), refs.get("destination")
            if event["event_type"] == "network.flow" and source and destination:
                _add_edge(edges, source, destination, "CONNECTED_TO", timestamp, oid)
                service = _ephemeral_entity_id("service", f"{destination}:{event['payload']['destination'].get('port', 0)}")
                nodes.setdefault(service, _entity_node(service, "service", "ephemeral_graph_projection"))
                _add_edge(edges, source, service, "ACCESSED_SERVICE", timestamp, oid)
            elif event["event_type"] == "http.request" and source:
                url = _ephemeral_entity_id("url", f"{event['payload'].get('host','')}{event['payload'].get('path','')}")
                nodes.setdefault(url, _entity_node(url, "url", "ephemeral_graph_projection"))
                _add_edge(edges, source, url, "REQUESTED", timestamp, oid)
            elif event["event_type"] == "auth.attempt":
                account = event["payload"]["account_entity_id"]; service = event["payload"].get("target_service_entity_id")
                nodes.setdefault(account, _entity_node(account, "account", "external_entity_reference"))
                if service:
                    nodes.setdefault(service, _entity_node(service, "service", "external_entity_reference"))
                    _add_edge(edges, account, service, "AUTHENTICATED_TO", timestamp, oid)
            elif event["event_type"] == "dns.query" and source:
                domain = _ephemeral_entity_id("domain", event["payload"]["question_name"])
                nodes.setdefault(domain, _entity_node(domain, "domain", "ephemeral_graph_projection"))
                _add_edge(edges, source, domain, "QUERIED", timestamp, oid)
    for detection, observation in zip(detections or [], observations):
        did = detection["result_id"]
        nodes[did] = {"node_id": did, "node_type": "detection_result", "entity_type": None, "canonical_ref": detection["canonical_digest"], "identity_scope": "artifact"}
        _add_edge(edges, did, observation["bundle_id"], "SUPPORTED_BY", observation["window"]["end"], observation["bundle_id"])
    docker_refs = sorted(docker_evidence_refs or [], key=lambda row: canonical_digest(row))
    for item in docker_refs:
        for container_id in item.get("container_ids", []):
            entity = _ephemeral_entity_id("container", container_id)
            nodes.setdefault(entity, _entity_node(entity, "container", "ephemeral_graph_projection"))
    base = {"schema_version": "interaction_graph_v1", "nodes": sorted(nodes.values(), key=lambda row: row["node_id"]), "edges": sorted(edges.values(), key=lambda row: (row["first_seen"], row["edge_type"], row["source"], row["target"])), "source_observations": [row["bundle_id"] for row in observations], "docker_evidence_refs": docker_refs}
    result = with_digest(base, id_field="graph_id", id_prefix="graph")
    validate_interaction_graph(result)
    return result


def validate_interaction_graph(graph: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("interaction_graph_v1.schema.json", graph); verify_digest(graph)
    node_ids = {row["node_id"] for row in graph["nodes"]}
    if len(node_ids) != len(graph["nodes"]) or any(row["node_type"] not in NODE_TYPES for row in graph["nodes"]):
        raise ContractError("invalid graph nodes")
    for node in graph["nodes"]:
        if node["node_type"] != "entity":
            continue
        if node.get("canonical_ref") is not None:
            raise ContractError("graph entity cannot claim canonical identity")
        if node.get("identity_scope") not in {"external_entity_reference", "ephemeral_graph_projection"}:
            raise ContractError("graph entity identity scope is required")
        if node["identity_scope"] == "ephemeral_graph_projection" and not node["node_id"].startswith("eph_"):
            raise ContractError("ephemeral graph entity identity mismatch")
        if node["identity_scope"] == "external_entity_reference" and not node["node_id"].startswith("ent_"):
            raise ContractError("external graph entity reference mismatch")
    for edge in graph["edges"]:
        if edge["edge_type"] not in EDGE_TYPES or edge["source"] not in node_ids or edge["target"] not in node_ids or edge["first_seen"] > edge["last_seen"] or edge["count"] < 1:
            raise ContractError("invalid typed temporal graph edge")
    assert_no_ground_truth_leakage(graph)
    return graph


def graph_feature_values(graph: dict[str, Any], previous_graph: dict[str, Any] | None = None) -> dict[str, float]:
    validate_interaction_graph(graph)
    entity_ids = {row["node_id"] for row in graph["nodes"] if row["node_type"] == "entity"}
    entity_types = {row["node_id"]: row.get("entity_type") for row in graph["nodes"]}
    edges = [row for row in graph["edges"] if row["source"] in entity_ids and row["target"] in entity_ids]
    out = Counter(row["source"] for row in edges); incoming = Counter(row["target"] for row in edges)
    weights = Counter(); neighbors: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        weights[edge["source"]] += edge["count"]; weights[edge["target"]] += edge["count"]
        neighbors[edge["source"]].add(edge["target"]); neighbors[edge["target"]].add(edge["source"])
    edge_types = Counter(row["edge_type"] for row in edges); total = len(edges)
    entropy = -sum((count/total)*math.log2(count/total) for count in edge_types.values()) if total else 0.0
    max_entropy = math.log2(len(edge_types)) if len(edge_types) > 1 else 1.0
    previous_degree = len(previous_graph["edges"]) if previous_graph else 0
    service_edges = [row for row in edges if entity_types.get(row["target"]) == "service"]
    service_counts = Counter(row["target"] for row in service_edges)
    account_host = defaultdict(set); host_account = defaultdict(set)
    for row in edges:
        if row["edge_type"] == "AUTHENTICATED_TO":
            account_host[row["source"]].add(row["target"]); host_account[row["target"]].add(row["source"])
    n = len(entity_ids)
    return {
        "out_degree": float(sum(out.values())), "in_degree": float(sum(incoming.values())), "weighted_degree": float(sum(weights.values())),
        "unique_neighbor_count": float(len(set().union(*neighbors.values())) if neighbors else 0), "edge_type_distribution": entropy/max_entropy if max_entropy else 0.0,
        "repeated_edge_ratio": sum(row["count"] > 1 for row in edges)/total if total else 0.0, "new_neighbor_ratio": sum(row["count"] == 1 for row in edges)/total if total else 0.0,
        "degree_change": float(len(graph["edges"]) - previous_degree), "local_density": total/(n*(n-1)) if n > 1 else 0.0,
        "temporal_edge_recurrence": sum(len(row["observation_ids"]) > 1 for row in edges)/total if total else 0.0,
        "service_concentration": max(service_counts.values(), default=0)/len(service_edges) if service_edges else 0.0,
        "account_host_fan_out": sum(map(len, account_host.values()))/len(account_host) if account_host else 0.0,
        "host_account_fan_in": sum(map(len, host_account.values()))/len(host_account) if host_account else 0.0,
    }


def attach_reasoning_nodes(graph: dict[str, Any], correlation: dict[str, Any], incident: dict[str, Any]) -> dict[str, Any]:
    """Добавляет к копии графа результаты reasoning, не меняя входной граф."""
    validate_interaction_graph(graph)
    nodes = {row["node_id"]: deepcopy(row) for row in graph["nodes"]}
    nodes[correlation["correlation_id"]] = {"node_id":correlation["correlation_id"],"node_type":"correlation_result","entity_type":None,"canonical_ref":correlation["canonical_digest"],"identity_scope":"artifact"}
    nodes[incident["candidate_id"]] = {"node_id":incident["candidate_id"],"node_type":"incident_candidate","entity_type":None,"canonical_ref":incident["canonical_digest"],"identity_scope":"artifact"}
    edge_map = {(row["source"],row["target"],row["edge_type"],row["direction"]):deepcopy(row) for row in graph["edges"]}
    end = correlation["time_range"]["end"]
    for observation in correlation["linked_observations"]:
        _add_edge(edge_map, correlation["correlation_id"], observation["bundle_id"], "ASSOCIATED_WITH", end, observation["bundle_id"])
    if correlation["contradictory_evidence"]:
        _add_edge(edge_map, correlation["correlation_id"], correlation["linked_observations"][-1]["bundle_id"], "CONTRADICTS", end, correlation["linked_observations"][-1]["bundle_id"])
    _add_edge(edge_map, incident["candidate_id"], correlation["correlation_id"], "SUPPORTED_BY", end, correlation["linked_observations"][-1]["bundle_id"])
    base={"schema_version":"interaction_graph_v1","nodes":sorted(nodes.values(),key=lambda row:row["node_id"]),"edges":sorted(edge_map.values(),key=lambda row:(row["first_seen"],row["edge_type"],row["source"],row["target"])),"source_observations":graph["source_observations"],"docker_evidence_refs":graph["docker_evidence_refs"]}
    result=with_digest(base,id_field="graph_id",id_prefix="graph"); return validate_interaction_graph(result)
