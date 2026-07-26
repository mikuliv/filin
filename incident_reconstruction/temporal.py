"""Детерминированная реконструкция временных и структурных отношений v0.4.1."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Any

from .canonical import sha256_hex, stable_id
from .validation import validate_bundle

BUILDER_VERSION = "v0.4.1-r1"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _precision(value: str) -> tuple[str, int]:
    fraction = value.partition(".")[2].rstrip("Z")
    if len(fraction) >= 6:
        return "microsecond", 0
    if len(fraction) >= 3:
        return "millisecond", 0
    return "second", 999


def _identified(prefix: str, field: str, value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result[field] = stable_id(prefix, value)
    return result


def _time(value: str, evidence_ids: list[str]) -> dict[str, Any]:
    precision, uncertainty = _precision(value)
    base = {
        "schema_version": "normalized_time_v1", "source_value": value,
        "normalized_utc": _iso(_dt(value)), "precision": precision,
        "clock_domain": "shadow_event_observation_utc", "uncertainty_before_ms": 0,
        "uncertainty_after_ms": uncertainty, "source_evidence_ids": sorted(evidence_ids),
        "validation_status": "validated", "limitations": ["Точность выведена только из представления исходной отметки времени."],
    }
    return _identified("time", "time_id", base)


def _interval(fact: dict[str, Any], time: dict[str, Any], event_ids: list[str]) -> dict[str, Any]:
    start = _dt(time["normalized_utc"])
    end_value = fact.get("end_time") or fact["start_time"]
    end = _dt(end_value)
    end_time = _time(end_value, fact["evidence_ids"])
    before = timedelta(milliseconds=time["uncertainty_before_ms"])
    after = timedelta(milliseconds=time["uncertainty_after_ms"])
    end_after = timedelta(milliseconds=end_time["uncertainty_after_ms"])
    base = {
        "schema_version": "normalized_time_interval_v1", "earliest_start": _iso(start - before),
        "latest_start": _iso(start + after), "earliest_end": _iso(end), "latest_end": _iso(end + end_after),
        "start_time_id": time["time_id"], "end_time_id": end_time["time_id"],
        "interval_status": "open_boundary" if fact.get("end_time") is None else ("exact" if not after and not end_after else "bounded_uncertainty"),
        "source_fact_ids": [fact["fact_id"]], "source_event_ids": sorted(event_ids),
        "limitations": (["Окончание наблюдаемого интервала отсутствует; точка не считается установленным окончанием."] if fact.get("end_time") is None else []),
    }
    return _identified("int", "interval_id", base)


def _relation_type(left: dict[str, Any], right: dict[str, Any]) -> tuple[str, str]:
    ls, le = _dt(left["earliest_start"]), _dt(left["latest_end"])
    rs, re = _dt(right["earliest_start"]), _dt(right["latest_end"])
    if le < rs: return "strictly_before", "strictly_after"
    if re < ls: return "strictly_after", "strictly_before"
    if le == rs: return "meets", "meets"
    if ls == rs and le == re: return "equal_interval", "equal_interval"
    if ls <= rs and le >= re: return "contains", "during"
    if rs <= ls and re >= le: return "during", "contains"
    if ls < re and rs < le: return "overlaps", "overlaps"
    return "simultaneous_within_precision", "simultaneous_within_precision"


def _temporal_pair(left: dict[str, Any], right: dict[str, Any], facts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    lt, rt = _relation_type(left, right)
    lf, rf = left["source_fact_ids"][0], right["source_fact_ids"][0]
    evidence = sorted(set(facts[lf]["evidence_ids"] + facts[rf]["evidence_ids"]))
    def core(a: dict[str, Any], b: dict[str, Any], relation_type: str) -> dict[str, Any]:
        return {"schema_version":"temporal_relation_v1","left_entity_id":a["interval_id"],"right_entity_id":b["interval_id"],"relation_type":relation_type,"relation_certainty":"certain" if relation_type not in {"simultaneous_within_precision","indeterminate"} else "bounded","derivation_basis":"normalized_interval_arithmetic_r1","supporting_time_ids":sorted({a["start_time_id"],a["end_time_id"],b["start_time_id"],b["end_time_id"]}),"supporting_fact_ids":sorted({lf,rf}),"supporting_evidence_ids":evidence,"inverse_relation_id":None,"derived":True,"limitations":["Временное отношение не является причинным отношением."]}
    a, b = core(left, right, lt), core(right, left, rt)
    a["relation_id"], b["relation_id"] = stable_id("trel", a), stable_id("trel", b)
    a["inverse_relation_id"], b["inverse_relation_id"] = b["relation_id"], a["relation_id"]
    return [a, b]


def _fact_relation(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    shared = sorted(set(left["evidence_ids"]) & set(right["evidence_ids"]))
    if shared: kind, basis, certainty = "same_passive_event", "shared_source_evidence", "certain"
    elif left["subject"] == right["subject"]: kind, basis, certainty = "same_observed_subject", "equal_observed_subject", "certain"
    else: kind, basis, certainty = "unrelated_within_available_evidence", "no_allowed_structural_basis", "indeterminate"
    base = {"schema_version":"fact_relation_v1","left_fact_id":left["fact_id"],"right_fact_id":right["fact_id"],"relation_type":kind,"relation_basis":basis,"supporting_evidence_ids":shared,"certainty":certainty,"symmetric":True,"limitations":["Совпадение класса модели и близость времени не использовались как основание."]}
    return _identified("frel", "relation_id", base)


def _gap(kind: str, entities: list[str], evidence: list[str], missing: str) -> dict[str, Any]:
    base = {"schema_version":"reconstruction_gap_v1","gap_type":kind,"affected_entity_ids":sorted(entities),"detected_between":sorted(entities)[:2],"basis":"explicit_missing_or_uncertain_source_information","missing_information":[missing],"effect_on_reconstruction":"Ограничивает строгость временной или структурной реконструкции.","resolvable":True,"suggested_manual_check":"Проверить первичный источник и версию подтверждающего материала.","evidence_ids":sorted(evidence),"limitations":["Разрыв не заменяется вымышленным наблюдаемым фактом."]}
    return _identified("gap", "gap_id", base)


def build_temporal_reconstruction(source_bundle: dict[str, Any]) -> dict[str, Any]:
    validate_bundle(source_bundle)
    card = source_bundle["incident_card"]
    facts = {x["fact_id"]: x for x in card["observed_facts"]}
    evidence_events = {x["evidence_id"]: x["source_id"] for x in card["evidence_references"]}
    times, intervals, gaps = [], [], []
    for fact in sorted(facts.values(), key=lambda x: x["fact_id"]):
        time = _time(fact["start_time"], fact["evidence_ids"])
        if all(existing["time_id"] != time["time_id"] for existing in times): times.append(time)
        events = sorted({evidence_events[e] for e in fact["evidence_ids"]})
        interval = _interval(fact, time, events); intervals.append(interval)
        if fact.get("end_time") is None: gaps.append(_gap("missing_interval_boundary", [fact["fact_id"]], fact["evidence_ids"], "observed_interval_end"))
    temporal = [r for a,b in combinations(intervals,2) for r in _temporal_pair(a,b,facts)]
    structural = [_fact_relation(a,b) for a,b in combinations(sorted(facts.values(),key=lambda x:x["fact_id"]),2)]
    groups=[]
    for evidence_id in sorted(evidence_events):
        members=sorted(f["fact_id"] for f in facts.values() if evidence_id in f["evidence_ids"])
        if len(members)>1:
            rels=sorted(r["relation_id"] for r in structural if r["left_fact_id"] in members and r["right_fact_id"] in members)
            base={"schema_version":"correlation_group_v1","group_type":"structural","member_fact_ids":members,"member_event_ids":[evidence_events[evidence_id]],"member_episode_ids":[],"grouping_rule_id":"shared_passive_event_r1","grouping_basis":"Общий неизменяемый источник passive event.","relation_ids":rels,"status":"deterministic_structural_group","missing_evidence":[],"limitations":["Группа не является подтверждённым инцидентом."]}
            groups.append(_identified("grp","group_id",base))
    strict=sorted([ [r["left_entity_id"],r["right_entity_id"]] for r in temporal if r["relation_type"]=="strictly_before"])
    graph_seed={"schema_version":"reconstruction_graph_v1","node_ids":sorted([x["interval_id"] for x in intervals]+list(facts)),"temporal_relation_ids":sorted(x["relation_id"] for x in temporal),"fact_relation_ids":sorted(x["relation_id"] for x in structural),"correlation_group_ids":sorted(x["group_id"] for x in groups),"gap_ids":sorted(x["gap_id"] for x in gaps),"strict_temporal_order":strict,"unresolved_relations":sorted(x["relation_id"] for x in temporal if x["relation_type"]=="indeterminate"),"graph_invariants":["strict_temporal_graph_acyclic","all_references_resolved","no_causal_relations"],"limitations":["Граф выражает только проверяемые временные и структурные отношения."]}
    graph={**graph_seed,"graph_id":stable_id("graph",graph_seed),"canonical_sha256":sha256_hex(graph_seed)}
    seed={"schema_version":"temporal_reconstruction_v1","source_card_id":card["card_id"],"source_bundle_id":source_bundle["manifest"]["bundle_id"],"normalized_times":sorted(times,key=lambda x:x["time_id"]),"normalized_intervals":sorted(intervals,key=lambda x:x["interval_id"]),"timeline_items":card["timeline"],"temporal_relations":sorted(temporal,key=lambda x:x["relation_id"]),"fact_relations":sorted(structural,key=lambda x:x["relation_id"]),"correlation_groups":sorted(groups,key=lambda x:x["group_id"]),"gaps":sorted(gaps,key=lambda x:x["gap_id"]),"reconstruction_graph":graph,"reconstruction_status":"partial" if gaps else "complete_within_available_evidence","deterministic_build":True,"limitations":["Результат лабораторный и не устанавливает причину инцидента."]}
    result={**seed,"reconstruction_id":stable_id("trc",seed),"canonical_sha256":sha256_hex(seed)}
    from .temporal_validation import validate_temporal_reconstruction
    validate_temporal_reconstruction(result, source_bundle)
    return result


def build_temporal_bundle(source_bundle: dict[str, Any]) -> dict[str, Any]:
    reconstruction=build_temporal_reconstruction(source_bundle)
    source_sha=sha256_hex(source_bundle); semantic=sha256_hex(reconstruction)
    bundle={"schema_version":"temporal_reconstruction_bundle_v1","source_bundle_sha256":source_sha,"source_bundle":source_bundle,"temporal_reconstruction":reconstruction,"reconstruction_graph":reconstruction["reconstruction_graph"],"gaps":reconstruction["gaps"],"build_journal":{"steps":["source_bundle_validated","times_normalized","relations_derived","gaps_recorded","graph_validated"],"semantic_result_sha256":semantic},"builder_version":BUILDER_VERSION,"manifest":{"files":[{"path":"source_bundle.json","sha256":source_sha},{"path":"temporal_reconstruction.json","sha256":semantic}],"semantic_result_sha256":semantic},"checksums":{"source_bundle.json":source_sha,"temporal_reconstruction.json":semantic},"standalone_verification":"passed","policy_result":{"causal_relations":0,"automatic_actions":0},"reproducibility":{"canonical_json":"utf8_sorted_keys_compact","deterministic_rebuild":True,"git_required":False,"network_required":False,"model_required":False,"backend_required":False}}
    from .temporal_validation import validate_temporal_bundle
    validate_temporal_bundle(bundle)
    return bundle


def explain_relation(reconstruction: dict[str, Any], relation_id: str) -> dict[str, Any]:
    relation=next((x for k in ("temporal_relations","fact_relations") for x in reconstruction[k] if x["relation_id"]==relation_id),None)
    if relation is None: raise KeyError(relation_id)
    times={x["time_id"]:x for x in reconstruction["normalized_times"]}
    tids=relation.get("supporting_time_ids",[])
    return {"schema_version":"relation_explanation_v1","relation_id":relation_id,"left_entity":relation.get("left_entity_id",relation.get("left_fact_id")),"right_entity":relation.get("right_entity_id",relation.get("right_fact_id")),"relation_type":relation["relation_type"],"basis":relation.get("derivation_basis",relation.get("relation_basis")),"source_times":[times[x]["source_value"] for x in tids if x in times],"precision":[times[x]["precision"] for x in tids if x in times],"uncertainty":[times[x]["uncertainty_after_ms"] for x in tids if x in times],"supporting_fact_ids":relation.get("supporting_fact_ids",[relation.get("left_fact_id"),relation.get("right_fact_id")]),"supporting_evidence_ids":relation.get("supporting_evidence_ids",[]),"applied_rule":relation.get("derivation_basis",relation.get("relation_basis")),"limitations":relation["limitations"],"derived":relation.get("derived",True)}
