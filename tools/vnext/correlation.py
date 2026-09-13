"""Инженерная многооконная корреляция, кандидаты инцидентов и ATT&CK vNext."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .context import context_fact_state, ordering_status
from .contracts import ContractError, canonical_digest, validate_json_schema_instance
from .graph import validate_interaction_graph
from .telemetry import validate_observation_bundle, verify_digest, with_digest


FORBIDDEN_CORRELATION_KEYS = {"scenario_id", "scenario_variant", "generator_id", "generator_family", "expected_taxonomy_node", "sealed_ground_truth", "ground_truth", "ground_truth_ref", "realization_id", "realization_metadata", "attack_label", "label_id"}
HYPOTHESES = {"reconnaissance_progression", "credential_abuse_recurrence", "c2_like_persistence", "benign_monitoring", "possible_lateral_activity"}


def assert_correlation_leakage_free(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_CORRELATION_KEYS:
                raise ContractError(f"forbidden correlation input: {key}")
            assert_correlation_leakage_free(nested)
    elif isinstance(value, list):
        for nested in value: assert_correlation_leakage_free(nested)


def _groups(features: list[dict[str, Any]], group_id: str) -> list[dict[str, float]]:
    return [group["values"] for bundle in features for group in bundle["groups"] if group["group_id"] == group_id and group["status"] == "AVAILABLE"]


def _mean(rows: list[dict[str, float]], key: str) -> float:
    values = [float(row.get(key, 0)) for row in rows]
    return sum(values)/len(values) if values else 0.0


def _active_context(context: dict[str, Any] | None, fact_type: str, as_of: str) -> list[dict[str, Any]]:
    if not context: return []
    return [fact for fact in context["facts"] if fact["fact_type"] == fact_type and context_fact_state(fact, as_of, stale_after_seconds=86400) == "ACTIVE"]


def correlate(observations: list[dict[str, Any]], features: list[dict[str, Any]], detections: list[dict[str, Any]], graph: dict[str, Any], context: dict[str, Any] | None, *, allowed_lateness_seconds: float = 10, watermark: str | None = None) -> dict[str, Any]:
    if not (len(observations) == len(features) == len(detections)) or len(observations) < 2:
        raise ContractError("correlation requires aligned multiple windows")
    assert_correlation_leakage_free([observations, features, detections, graph, context]); validate_interaction_graph(graph)
    for observation in observations: validate_observation_bundle(observation)
    network = _groups(features, "network_context_v1"); temporal = _groups(features, "temporal_v1"); auth = _groups(features, "authentication_v1"); http = _groups(features, "http_behavior_v1"); graph_groups = _groups(features, "interaction_graph_v1")
    evidence: list[dict[str, Any]] = []; contradictions: list[dict[str, Any]] = []; scored: dict[str, float] = defaultdict(float)
    recurrence = _mean(network, "cross_window_recurrence"); port_fanout = max((row.get("port_fan_out", 0) for row in network), default=0); endpoint_stability = _mean(network, "endpoint_stability")
    if port_fanout > 1:
        scored["reconnaissance_progression"] += min(0.55, port_fanout/10); evidence.append({"evidence_id":"corr_recon_fanout","kind":"network_context","value":port_fanout})
    if recurrence > 0:
        scored["reconnaissance_progression"] += 0.35*recurrence; evidence.append({"evidence_id":"corr_recurrence","kind":"historical_recurrence","value":recurrence})
    failures = sum(row.get("failure_count", 0) for row in auth); accounts = max((row.get("unique_accounts", 0) for row in auth), default=0)
    if failures:
        scored["credential_abuse_recurrence"] = min(0.8, failures/8 + accounts/8); evidence.append({"evidence_id":"corr_auth_failures","kind":"feature","value":failures})
    periodicity = _mean(temporal, "periodicity_score"); path_repeat = _mean(http, "repeated_path_ratio")
    if recurrence > 0 and endpoint_stability > 0:
        scored["c2_like_persistence"] = min(0.85, 0.3*recurrence + 0.25*endpoint_stability + 0.2*periodicity + 0.15*path_repeat)
        evidence.append({"evidence_id":"corr_endpoint_persistence","kind":"entity_relationship","value":endpoint_stability})
    end = max(row["window"]["end"] for row in observations)
    approved = _active_context(context, "approved_scanner_role", end); monitoring = _active_context(context, "monitoring_system_role", end); expected = _active_context(context, "expected_communication_relationship", end); maintenance = _active_context(context, "maintenance_window", end)
    new_targets = float(network[-1].get("new_target_ratio", 0)) if network else 0.0
    overlap = float(network[-1].get("historical_target_overlap", 0)) if network else 0.0
    context_drift = False
    if approved or monitoring:
        role_support = 0.25
        if expected: role_support += 0.25
        if recurrence > 0: role_support += 0.25*recurrence
        if maintenance: role_support += 0.1
        scored["benign_monitoring"] = role_support
        evidence.append({"evidence_id":"corr_context_role","kind":"context_fact","value":"active_declared_role"})
        if new_targets > overlap or port_fanout > max(2.0, _mean(network[:-1], "port_fan_out") * 1.5 if len(network)>1 else 2.0):
            context_drift = True
            contradictions.append({"evidence_id":"corr_context_drift","kind":"context_poisoning_guard","value":{"new_target_ratio":new_targets,"historical_overlap":overlap,"port_fan_out":port_fanout}})
            scored["benign_monitoring"] *= 0.35
        else:
            if approved and "reconnaissance_progression" in scored: scored["reconnaissance_progression"] *= 0.45
            if monitoring and expected and "c2_like_persistence" in scored: scored["c2_like_persistence"] *= 0.65
    auth_edges = [row for row in graph["edges"] if row["edge_type"] == "AUTHENTICATED_TO"]
    service_edges = [row for row in graph["edges"] if row["edge_type"] == "ACCESSED_SERVICE"]
    if auth_edges and service_edges and any(a["last_seen"] <= s["first_seen"] for a in auth_edges for s in service_edges):
        scored["possible_lateral_activity"] = min(0.8, 0.35 + 0.1*len(auth_edges) + 0.05*len(service_edges)); evidence.append({"evidence_id":"corr_auth_then_service","kind":"temporal_relation","value":True})
    ranked = sorted(scored.items(), key=lambda row: (-row[1], row[0])); top = ranked[0][1] if ranked else 0.0; margin = top-(ranked[1][1] if len(ranked)>1 else 0.0)
    reasons = []
    if top < 0.6: reasons.append("insufficient_support")
    if len(ranked)>1 and margin < 0.12: reasons.append("ambiguous_hypotheses")
    if contradictions and ranked and ranked[0][0] == "benign_monitoring": reasons.append("context_drift")
    hypotheses = [{"hypothesis_id": name, "support_score": score, "evidence_refs": [row["evidence_id"] for row in evidence if (name.startswith("reconnaissance") and row["evidence_id"].startswith("corr_recon")) or (name.startswith("credential") and row["evidence_id"]=="corr_auth_failures") or (name.startswith("c2") and row["evidence_id"]=="corr_endpoint_persistence") or (name=="benign_monitoring" and row["evidence_id"]=="corr_context_role") or (name=="possible_lateral_activity" and row["evidence_id"]=="corr_auth_then_service")], "alternative": index>0} for index,(name,score) in enumerate(ranked)]
    event_times = [row["temporal_summary"]["event_time"] for row in observations if row["temporal_summary"]["event_time"]]
    effective_watermark = watermark or (max(event_times) if event_times else None)
    statuses = sorted({ordering_status(row["temporal_summary"]["event_time"], row["temporal_summary"]["ingest_time"], effective_watermark, allowed_lateness_seconds) for row in observations})
    temporal_relations = [{"relation":"PRECEDES","left":a["bundle_id"],"right":b["bundle_id"]} for a,b in zip(observations, observations[1:])]
    entities = sorted({node["node_id"] for node in graph["nodes"] if node["node_type"] == "entity"})
    base = {"schema_version":"correlation_result_v1","linked_observations":[{"bundle_id":row["bundle_id"],"canonical_digest":row["canonical_digest"]} for row in observations],"linked_feature_bundles":[{"feature_bundle_id":row["feature_bundle_id"],"canonical_digest":row["canonical_digest"]} for row in features],"linked_detection_results":[{"result_id":row["result_id"],"canonical_digest":row["canonical_digest"]} for row in detections],"graph_ref":{"graph_id":graph["graph_id"],"canonical_digest":graph["canonical_digest"]},"context_ref":{"profile_id":context["profile_id"],"canonical_digest":context["canonical_digest"]} if context else None,"involved_entities":entities,"time_range":{"start":min(row["window"]["start"] for row in observations),"end":end},"hypotheses":hypotheses,"supporting_evidence":evidence,"contradictory_evidence":contradictions,"temporal_relations":temporal_relations,"support_score":top,"abstention":{"abstained":bool(reasons),"reasons":reasons,"final_state":"UNKNOWN" if reasons else "CONTEXTUAL_HYPOTHESIS"},"maturity":"implemented","ordering_statuses":statuses}
    result = with_digest(base,id_field="correlation_id",id_prefix="correlation"); validate_json_schema_instance("correlation_result_v1.schema.json",result); verify_digest(result); assert_correlation_leakage_free(result)
    return result


ATTACK_SUBSET = {
    "reconnaissance_progression": [("T1046","Network Service Discovery"),("T1018","Remote System Discovery")],
    "credential_abuse_recurrence": [("T1110","Brute Force"),("T1110.003","Password Spraying")],
    "c2_like_persistence": [("T1071.001","Web Protocols"),("T1105","Ingress Tool Transfer")],
    "possible_lateral_activity": [("T1021","Remote Services"),("T1078","Valid Accounts")],
}


def map_attack_evidence(correlation: dict[str, Any]) -> dict[str, Any]:
    assert_correlation_leakage_free(correlation)
    candidates=[]
    for hypothesis in correlation["hypotheses"]:
        for technique_id, name in ATTACK_SUBSET.get(hypothesis["hypothesis_id"], []):
            candidates.append({"technique_id":technique_id,"technique_name":name,"attack_reference":"https://attack.mitre.org/techniques/"+technique_id.replace(".","/"),"mapping_source":"manually_curated_engineering_subset_v1","supporting_evidence":hypothesis["evidence_refs"],"contradictory_evidence":[row["evidence_id"] for row in correlation["contradictory_evidence"]],"support_score":hypothesis["support_score"]})
    base={"schema_version":"attack_evidence_mapping_v1","mapping_id":"attack_map_"+canonical_digest(candidates),"knowledge_base":{"name":"MITRE ATT&CK","subset_version":"filin-engineering-v1","corpus_downloaded":False},"candidates":sorted(candidates,key=lambda row:(-row["support_score"],row["technique_id"]))}
    result=with_digest(base); validate_json_schema_instance("attack_evidence_mapping_v1.schema.json",result); verify_digest(result); return result


def build_attack_chain(correlation: dict[str, Any]) -> dict[str, Any]:
    ordered_names=[name for name in ("reconnaissance_progression","credential_abuse_recurrence","possible_lateral_activity","c2_like_persistence") if any(row["hypothesis_id"]==name for row in correlation["hypotheses"])]
    stages=[]
    for index,name in enumerate(ordered_names):
        hypothesis=next(row for row in correlation["hypotheses"] if row["hypothesis_id"]==name)
        stages.append({"stage_index":index,"behavior_hypothesis":name,"linked_entities":correlation["involved_entities"],"evidence":hypothesis["evidence_refs"],"temporal_relation":"PRECEDES" if index else "START","support_score":hypothesis["support_score"]})
    base={"schema_version":"attack_chain_hypothesis_v1","stages":stages,"alternatives":[row["hypothesis_id"] for row in correlation["hypotheses"] if row["hypothesis_id"] not in ordered_names],"support_score":correlation["support_score"],"status":"hypothesis"}
    result=with_digest(base,id_field="chain_id",id_prefix="chain"); validate_json_schema_instance("attack_chain_hypothesis_v1.schema.json",result); verify_digest(result); return result


def build_incident_candidate(correlation: dict[str, Any], attack_mapping: dict[str, Any], chain: dict[str, Any]) -> dict[str, Any]:
    assert_correlation_leakage_free([correlation,attack_mapping,chain])
    top=correlation["hypotheses"][0]["hypothesis_id"] if correlation["hypotheses"] else None
    status="NEEDS_MORE_EVIDENCE" if correlation["abstention"]["abstained"] else ("LIKELY_BENIGN" if top=="benign_monitoring" else "SUSPICIOUS")
    base={"schema_version":"incident_candidate_v1","time_range":correlation["time_range"],"entities":correlation["involved_entities"],"observations":[row["bundle_id"] for row in correlation["linked_observations"]],"detection_results":[row["result_id"] for row in correlation["linked_detection_results"]],"correlation_results":[correlation["correlation_id"]],"hypotheses":[chain["chain_id"]]+[row["hypothesis_id"] for row in correlation["hypotheses"]],"evidence":[row["evidence_id"] for row in correlation["supporting_evidence"]],"contradictions":[row["evidence_id"] for row in correlation["contradictory_evidence"]],"attack_candidates":[row["technique_id"] for row in attack_mapping["candidates"]],"support_score":correlation["support_score"],"status":status}
    result=with_digest(base,id_field="candidate_id",id_prefix="incident"); validate_json_schema_instance("incident_candidate_v1.schema.json",result); verify_digest(result); assert_correlation_leakage_free(result); return result


def build_correlation_registry() -> dict[str, Any]:
    specs=[("reconnaissance_progression_v1",["network_context_v1"],["network.flow"],["CONNECTED_TO","ACCESSED_SERVICE"],["approved_scanner_role","maintenance_window"]),("credential_abuse_recurrence_v1",["authentication_v1","interaction_graph_v1"],["auth.attempt"],["AUTHENTICATED_TO"],[]),("c2_like_persistence_v1",["temporal_v1","network_context_v1"],["network.flow","http.request"],["CONNECTED_TO","REQUESTED"],["expected_communication_relationship"]),("benign_monitoring_context_v1",["network_context_v1","temporal_v1"],["network.flow"],["CONNECTED_TO"],["monitoring_system_role"]),("possible_lateral_activity_v1",["authentication_v1","interaction_graph_v1"],["auth.attempt","network.flow"],["AUTHENTICATED_TO","ACCESSED_SERVICE"],[])]
    rows=[{"capability_id":cid,"version":"1.0.0","required_features":features,"required_telemetry":telemetry,"required_graph_edges":edges,"optional_context":context,"supported_behavior_families":[cid.rsplit("_v1",1)[0]],"maturity":"implemented","explanation_capability":True} for cid,features,telemetry,edges,context in specs]
    return with_digest({"schema_version":"correlation_registry_v1","registry_id":"filin_vnext_correlation_wave1","capabilities":rows})
