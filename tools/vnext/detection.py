"""Интерпретируемые baseline-детекторы vNext с отказом от конкретизации."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Protocol

from .contracts import CONTRACT_ROOT, ContractError, canonical_digest, load_json, validate_json_schema_instance
from .features import validate_feature_bundle
from .telemetry import GROUND_TRUTH_KEYS, verify_digest, with_digest


class Detector(Protocol):
    detector_id: str
    def evaluate(self, feature_bundle: dict[str, Any], configuration: dict[str, Any] | None = None) -> dict[str, Any]: ...


def _available(bundle: dict[str, Any]) -> dict[str, dict[str, float]]:
    return {group["group_id"]: group["values"] for group in bundle["groups"] if group["status"] == "AVAILABLE"}


def _evidence(feature: str, value: float | str | bool | None, reference: str, direction: str, hypothesis: str | None, template: str) -> dict[str, Any]:
    base = {"evidence_type": "feature", "source_feature": feature, "observed_value": value, "reference": reference, "direction": direction, "linked_hypothesis": hypothesis, "template_key": template}
    digest = canonical_digest(base); return {"evidence_id": "evidence_" + digest, **base}


class HeuristicDetector:
    detector_id = "vnext_heuristic_baseline_v1"
    def evaluate(self, feature_bundle, configuration=None):
        groups = _available(feature_bundle); scores: dict[str, float] = {}; evidence: list[dict[str, Any]] = []
        auth = groups.get("authentication_v1")
        if auth:
            failure, accounts, concentration, attempts = auth["failure_ratio"], auth["unique_accounts"], auth["max_account_concentration"], auth["attempt_count"]
            scores["malicious.credential_abuse.brute_force"] = failure * concentration * min(1.0, attempts/4)
            scores["malicious.credential_abuse.password_spraying"] = failure * min(1.0, accounts/4) * (1-concentration)
            scores["benign.authentication"] = failure * (0.65 if attempts <= 3 else 0.3)
            evidence += [_evidence("authentication_v1.failure_ratio", failure, ">=0.75", "supports", "malicious.credential_abuse.brute_force", "auth_failure_ratio_high"), _evidence("authentication_v1.unique_accounts", accounts, ">=3", "supports" if accounts >= 3 else "contradicts", "malicious.credential_abuse.password_spraying", "auth_account_fanout"), _evidence("authentication_v1.attempt_count", attempts, "<=3", "supports" if attempts <= 3 else "contradicts", "benign.authentication", "auth_small_retry_set")]
        http = groups.get("http_behavior_v1")
        temporal = groups.get("temporal_v1")
        if http:
            fanout, repetition, errors = http["path_fanout"], http["repeated_path_ratio"], http["error_ratio"]
            scores["malicious.reconnaissance.web_path_enumeration"] = 0.65*fanout + 0.35*errors
            evidence += [_evidence("http_behavior_v1.path_fanout", fanout, ">=0.6", "supports" if fanout >= .6 else "contradicts", "malicious.reconnaissance.web_path_enumeration", "http_path_fanout"), _evidence("http_behavior_v1.error_ratio", errors, ">=0.2", "supports" if errors >= .2 else "contradicts", "malicious.reconnaissance.web_path_enumeration", "http_error_ratio")]
            if temporal:
                periodic, jitter = temporal["periodicity_score"], temporal["jitter_estimate"]
                scores["malicious.command_and_control.beaconing"] = 0.55*periodic + 0.45*repetition
                scores["benign.operations.monitoring"] = 0.5*periodic + 0.3*(1-errors) + 0.2*http["get_share"]
                evidence += [_evidence("temporal_v1.periodicity_score", periodic, ">=0.7", "supports" if periodic >= .7 else "contradicts", "malicious.command_and_control.beaconing", "temporal_periodicity"), _evidence("temporal_v1.jitter_estimate", jitter, "<=0.15", "supports" if jitter <= .15 else "contradicts", "malicious.command_and_control.beaconing", "temporal_jitter"), _evidence("http_behavior_v1.error_ratio", errors, "near zero", "contradicts" if errors < .1 else "context_only", "malicious.command_and_control.beaconing", "benign_endpoint_health")]
        return {"detector_id": self.detector_id, "scores": scores, "evidence": evidence, "distance": None, "artifact_digest": canonical_digest({"detector": self.detector_id, "version": 1})}


class PrototypeDistanceDetector:
    detector_id = "vnext_prototype_distance_baseline_v1"
    PROTOTYPES = {
        "malicious.credential_abuse.brute_force": {"failure_ratio": 1.0, "account_scale": .25, "concentration": 1.0, "attempt_scale": 1.0},
        "malicious.credential_abuse.password_spraying": {"failure_ratio": 1.0, "account_scale": 1.0, "concentration": .25, "attempt_scale": 1.0},
        "benign.authentication": {"failure_ratio": 1.0, "account_scale": .25, "concentration": 1.0, "attempt_scale": .75},
        "malicious.reconnaissance.web_path_enumeration": {"path_fanout": 1.0, "error_ratio": .3, "repetition": 0.0},
        "malicious.command_and_control.beaconing": {"periodicity": .9, "jitter": .1, "repetition": .75},
        "benign.operations.monitoring": {"periodicity": .9, "jitter": .1, "repetition": .75},
    }
    def evaluate(self, feature_bundle, configuration=None):
        groups = _available(feature_bundle); vectors = []
        if "authentication_v1" in groups:
            a=groups["authentication_v1"]; vectors.append(({"failure_ratio":a["failure_ratio"],"account_scale":min(1,a["unique_accounts"]/4),"concentration":a["max_account_concentration"],"attempt_scale":min(1,a["attempt_count"]/4)}, "authentication"))
        if "http_behavior_v1" in groups:
            h=groups["http_behavior_v1"]; vectors.append(({"path_fanout":h["path_fanout"],"error_ratio":h["error_ratio"],"repetition":h["repeated_path_ratio"]}, "http"))
        if "temporal_v1" in groups and "http_behavior_v1" in groups:
            t=groups["temporal_v1"]; h=groups["http_behavior_v1"]; vectors.append(({"periodicity":t["periodicity_score"],"jitter":min(1,t["jitter_estimate"]),"repetition":h["repeated_path_ratio"]}, "temporal"))
        distances = {}
        for node, prototype in self.PROTOTYPES.items():
            compatible = [vector for vector,_ in vectors if set(vector) == set(prototype)]
            if compatible: distances[node] = min(math.sqrt(sum((vector[key]-prototype[key])**2 for key in prototype)/len(prototype)) for vector in compatible)
        scores = {node: max(0.0, 1-distance) for node,distance in distances.items()}
        nearest = min(distances.values()) if distances else 1.0
        evidence = [_evidence("prototype_distance", nearest, "<=0.35", "supports" if nearest <= .35 else "contradicts", min(distances, key=distances.get) if distances else None, "prototype_nearest_distance")]
        return {"detector_id": self.detector_id, "scores": scores, "evidence": evidence, "distance": nearest, "artifact_digest": canonical_digest({"detector": self.detector_id, "prototypes": self.PROTOTYPES})}


DETECTORS: tuple[Detector, ...] = (HeuristicDetector(), PrototypeDistanceDetector())


def _assert_prediction_input(value: Any) -> None:
    forbidden = GROUND_TRUTH_KEYS | {"expected_taxonomy_node", "execution_secret", "generator_family"}
    def walk(item):
        if isinstance(item, dict):
            for key, nested in item.items():
                if key in forbidden: raise ContractError(f"forbidden prediction input: {key}")
                walk(nested)
        elif isinstance(item, list):
            for nested in item: walk(nested)
    walk(value)


def detect(feature_bundle: dict[str, Any], configuration: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    _assert_prediction_input(feature_bundle); validate_feature_bundle(feature_bundle)
    configuration = configuration or {}
    requested = configuration.get("detector_ids", [detector.detector_id for detector in DETECTORS])
    selected = [detector for detector in DETECTORS if detector.detector_id in requested]
    if not selected or {detector.detector_id for detector in selected} != set(requested): raise ContractError("detector capability mismatch")
    outputs = [detector.evaluate(feature_bundle, configuration) for detector in selected]
    combined: dict[str, list[float]] = defaultdict(list)
    evidence_by_id = {}
    for output in outputs:
        for node, score in output["scores"].items(): combined[node].append(score)
        for item in output["evidence"]: evidence_by_id[item["evidence_id"]] = item
    ranked = sorted(((node, sum(scores)/len(scores)) for node,scores in combined.items()), key=lambda item: (-item[1], item[0]))
    available = {group["group_id"] for group in feature_bundle["groups"] if group["status"] == "AVAILABLE"}
    top = ranked[0][1] if ranked else 0.0; second = ranked[1][1] if len(ranked)>1 else 0.0; margin = top-second
    nearest_distance = outputs[1]["distance"] if len(outputs)>1 else None
    top_by_detector = [max(output["scores"], key=output["scores"].get) for output in outputs if output["scores"]]
    disagreement = len(set(top_by_detector)) > 1
    reasons=[]
    if not available.intersection({"authentication_v1","http_behavior_v1"}): reasons.append("insufficient_telemetry")
    if margin < .12: reasons.append("low_hypothesis_margin")
    if nearest_distance is None or nearest_distance > .42: reasons.append("excessive_prototype_distance")
    if disagreement: reasons.append("detector_disagreement")
    abstained = bool(reasons); known = not abstained and bool(ranked)
    suspicious = "insufficient_evidence" if not ranked else ("suspicious" if top >= .45 else "benign_like")
    hypotheses=[]
    for rank,(node,score) in enumerate(ranked[:5],1):
        refs=[item["evidence_id"] for item in evidence_by_id.values() if item["linked_hypothesis"] == node]
        contradictory=[item["evidence_id"] for item in evidence_by_id.values() if item["linked_hypothesis"] == node and item["direction"] == "contradicts"]
        groups=sorted({item["source_feature"].split(".")[0] for item in evidence_by_id.values() if item["evidence_id"] in refs})
        sources=[output["detector_id"] for output in outputs if node in output["scores"]]
        hypotheses.append({"taxonomy_node_id":node,"support_score":score,"rank":rank,"evidence_refs":refs,"supporting_feature_groups":groups,"contradictory_evidence_refs":contradictory,"detector_sources":sources})
    for raw in feature_bundle["raw_evidence_refs"]:
        item = _evidence("observation.raw_evidence", raw["evidence_id"], raw["sha256"], "context_only", None, "raw_evidence_reference")
        item["evidence_type"] = "raw"; evidence_by_id[item["evidence_id"]] = item
    for output in outputs:
        decision = max(output["scores"], key=output["scores"].get) if output["scores"] else None
        item = _evidence(output["detector_id"], max(output["scores"].values(), default=0.0), decision or "insufficient_evidence", "context_only", decision, "detector_rationale")
        item["evidence_type"] = "detector_rationale"; evidence_by_id[item["evidence_id"]] = item
    for hypothesis in hypotheses:
        item = _evidence("combined_hypothesis_support", hypothesis["support_score"], f"rank={hypothesis['rank']}", "supports", hypothesis["taxonomy_node_id"], "ranked_hypothesis")
        item["evidence_type"] = "hypothesis"; evidence_by_id[item["evidence_id"]] = item
        hypothesis["evidence_refs"].append(item["evidence_id"])
    family = hypotheses[0]["taxonomy_node_id"].rsplit(".",1)[0] if hypotheses else None
    base={"schema_version":"detection_result_v2","feature_bundle_ref":{"feature_bundle_id":feature_bundle["feature_bundle_id"],"canonical_digest":feature_bundle["canonical_digest"]},"stages":{"suspiciousness":suspicious,"behavioral_family":family,"specific_behavior":hypotheses[0]["taxonomy_node_id"] if known else None},"known_behavior":known,"hypotheses":hypotheses,
          "detector_outputs":[{"detector_id":o["detector_id"],"score":max(o["scores"].values(),default=0.0),"decision":max(o["scores"],key=o["scores"].get) if o["scores"] else "insufficient_evidence","distance":o["distance"],"artifact_digest":o["artifact_digest"]} for o in outputs],
          "abstention":{"abstained":abstained,"reasons":reasons,"signals":{"hypothesis_margin":margin,"nearest_distance":nearest_distance if nearest_distance is not None else 1.0,"detector_disagreement":disagreement,"available_group_count":len(available)}},"evidence_refs":sorted(evidence_by_id),"ground_truth_used":False,"limitations":["Эвристические оценки не являются вероятностями и не прошли экспериментальную калибровку."]}
    result=with_digest(base,id_field="result_id",id_prefix="detection"); validate_detection_result(result)
    explanation_base={"schema_version":"explanation_bundle_v2","detection_result_ref":result["result_id"],"layers":{"raw_evidence_refs":[item["evidence_id"] for item in evidence_by_id.values() if item["evidence_type"]=="raw"],"feature_evidence_refs":[item["evidence_id"] for item in evidence_by_id.values() if item["evidence_type"]=="feature"],"detector_rationale_refs":[item["evidence_id"] for item in evidence_by_id.values() if item["evidence_type"]=="detector_rationale"],"hypothesis_refs":[item["evidence_id"] for item in evidence_by_id.values() if item["evidence_type"]=="hypothesis"]},"evidence_items":list(evidence_by_id.values()),"hypothesis_explanations":[{"taxonomy_node_id":h["taxonomy_node_id"],"supporting_refs":h["evidence_refs"],"contradicting_refs":h["contradictory_evidence_refs"]} for h in hypotheses],"ground_truth_used":False,"limitations":["Человекочитаемый повествовательный слой намеренно не создаётся."]}
    explanation=with_digest(explanation_base,id_field="explanation_id",id_prefix="explanation"); validate_explanation(explanation,result)
    return result,explanation


def validate_detection_result(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("detection_result_v2.schema.json",value); verify_digest(value)
    if value["ground_truth_used"] is not False: raise ContractError("ground truth is forbidden on prediction path")
    ranks=[item["rank"] for item in value["hypotheses"]]
    if ranks != list(range(1,len(ranks)+1)): raise ContractError("hypothesis ranks are not canonical")
    scores=[item["support_score"] for item in value["hypotheses"]]
    if scores != sorted(scores,reverse=True): raise ContractError("hypotheses are not score-ranked")
    return value


def validate_explanation(value: dict[str, Any], result: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_json_schema_instance("explanation_bundle_v2.schema.json",value); verify_digest(value)
    ids={item["evidence_id"] for item in value["evidence_items"]}
    if result and (value["detection_result_ref"] != result["result_id"] or set(result["evidence_refs"])-ids): raise ContractError("explanation evidence linkage mismatch")
    return value


def build_detector_registry() -> dict[str, Any]:
    nodes=sorted({node for detector in DETECTORS if hasattr(detector,"PROTOTYPES") for node in detector.PROTOTYPES} | {"malicious.credential_abuse.brute_force","malicious.credential_abuse.password_spraying","malicious.reconnaissance.web_path_enumeration","malicious.command_and_control.beaconing","benign.authentication","benign.operations.monitoring"})
    rows=[{"detector_id":"vnext_heuristic_baseline_v1","detector_type":"deterministic_rule","implementation_ref":"tools.vnext.detection.HeuristicDetector","required_feature_groups":["temporal_v1"],"optional_feature_groups":["authentication_v1","http_behavior_v1","dns_v1","legacy_network_v2"],"supported_taxonomy_nodes":nodes,"open_set_capability":True,"explanation_capability":True,"maturity":"implemented"},
          {"detector_id":"vnext_prototype_distance_baseline_v1","detector_type":"prototype_distance","implementation_ref":"tools.vnext.detection.PrototypeDistanceDetector","required_feature_groups":["temporal_v1"],"optional_feature_groups":["authentication_v1","http_behavior_v1"],"supported_taxonomy_nodes":nodes,"open_set_capability":True,"explanation_capability":True,"maturity":"implemented"}]
    return with_digest({"schema_version":"detector_capability_v1","registry_id":"filin_vnext_detectors_v1","status":"implemented","detectors":rows})


def validate_detector_registry(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("detector_capability_v1.schema.json", value); verify_digest(value)
    if len({row["detector_id"] for row in value["detectors"]}) != len(value["detectors"]): raise ContractError("duplicate detector")
    return value


def build_observability_matrix() -> dict[str, Any]:
    heuristic="vnext_heuristic_baseline_v1"; distance="vnext_prototype_distance_baseline_v1"
    def row(node, telemetry, groups, limitation): return {"taxonomy_node_id":node,"telemetry":telemetry,"feature_groups":groups,"detectors":[heuristic,distance],"limitations":[limitation]}
    rows=[
      row("malicious.reconnaissance.port_scanning",{"network.flow":"required"},{"legacy_network_v2":"partial","temporal_v1":"useful","http_behavior_v1":"unsupported"},"Текущий baseline не имеет отдельной flow fan-out группы."),
      row("malicious.reconnaissance.web_path_enumeration",{"network.flow":"required","http.request":"useful"},{"legacy_network_v2":"partial","temporal_v1":"useful","http_behavior_v1":"required"},"Метаданные не подтверждают exploit semantics."),
      row("malicious.credential_abuse.brute_force",{"auth.attempt":"required"},{"authentication_v1":"required","temporal_v1":"useful","legacy_network_v2":"partial"},"Истинное намерение не наблюдается."),
      row("malicious.credential_abuse.password_spraying",{"auth.attempt":"required"},{"authentication_v1":"required","temporal_v1":"useful","legacy_network_v2":"unsupported"},"Нужна достоверная идентичность источников."),
      row("malicious.command_and_control.beaconing",{"network.flow":"required","http.request":"useful"},{"temporal_v1":"required","http_behavior_v1":"useful","legacy_network_v2":"partial"},"Периодичность также характерна для мониторинга."),
      row("malicious.command_and_control.dns_c2",{"dns.query":"required","network.flow":"useful"},{"dns_v1":"required","temporal_v1":"required","legacy_network_v2":"partial"},"Генератор DNS остаётся planned."),
      row("benign.operations.monitoring",{"network.flow":"required","http.request":"useful"},{"temporal_v1":"required","http_behavior_v1":"useful","legacy_network_v2":"partial"},"Может быть неотличим от обратного вызова без контекста."),
      row("benign.authentication",{"auth.attempt":"required"},{"authentication_v1":"required","temporal_v1":"useful","legacy_network_v2":"unsupported"},"Причина ошибки требует внешнего разрешённого контекста.")]
    return with_digest({"schema_version":"behavior_observability_matrix_v1","matrix_id":"filin_vnext_observability_wave1","status":"implemented","rows":rows})


def validate_observability_matrix(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("behavior_observability_matrix_v1.schema.json",value); verify_digest(value)
    taxonomy={row["node_id"] for row in load_json(CONTRACT_ROOT/"behavior_taxonomy_v1.json")["nodes"]}
    detectors={row["detector_id"] for row in validate_detector_registry(load_json(CONTRACT_ROOT/"detector_capabilities_v1.json"))["detectors"]}
    if any(row["taxonomy_node_id"] not in taxonomy or set(row["detectors"])-detectors for row in value["rows"]): raise ContractError("observability matrix reference mismatch")
    return value
