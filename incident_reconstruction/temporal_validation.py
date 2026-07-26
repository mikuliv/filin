"""Контрактная и графовая проверка временной реконструкции v0.4.1."""
from __future__ import annotations
from typing import Any
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .canonical import sha256_hex
from .validation import ValidationFailure, validate_bundle

V041_CONTRACTS=Path(__file__).resolve().parent/"contracts/v0_4_1"

def validate_v041_schema(instance:Any,name:str)->None:
 schema=json.loads((V041_CONTRACTS/f"{name}.schema.json").read_text(encoding="utf-8"))
 errors=sorted(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(instance),key=lambda e:list(e.path))
 if errors:
  error=errors[0];raise ValidationFailure("schema_validation_failed",f"{name}:{'/'.join(map(str,error.path))}:{error.message}")

INVERSE={"strictly_before":"strictly_after","strictly_after":"strictly_before","contains":"during","during":"contains","overlaps":"overlaps","equal_interval":"equal_interval","simultaneous_within_precision":"simultaneous_within_precision","meets":"meets","indeterminate":"indeterminate"}

def _unique(items:list[dict[str,Any]],field:str,code:str)->dict[str,dict[str,Any]]:
 out={}
 for x in items:
  if x[field] in out: raise ValidationFailure(code,x[field])
  out[x[field]]=x
 return out

def _acyclic(edges:list[list[str]])->bool:
 graph={}
 for a,b in edges: graph.setdefault(a,set()).add(b)
 visiting=set(); done=set()
 def visit(n):
  if n in visiting:return False
  if n in done:return True
  visiting.add(n)
  if not all(visit(x) for x in graph.get(n,())):return False
  visiting.remove(n);done.add(n);return True
 return all(visit(n) for n in list(graph))

def validate_temporal_reconstruction(value:dict[str,Any],source_bundle:dict[str,Any])->dict[str,Any]:
 validate_bundle(source_bundle)
 for name,key in [("normalized_time_v1","normalized_times"),("normalized_time_interval_v1","normalized_intervals"),("temporal_relation_v1","temporal_relations"),("fact_relation_v1","fact_relations"),("correlation_group_v1","correlation_groups"),("reconstruction_gap_v1","gaps")]:
  for x in value[key]: validate_v041_schema(x,name)
 validate_v041_schema(value["reconstruction_graph"],"reconstruction_graph_v1")
 facts={x["fact_id"] for x in source_bundle["incident_card"]["observed_facts"]}; evidence={x["evidence_id"] for x in source_bundle["incident_card"]["evidence_references"]}
 times=_unique(value["normalized_times"],"time_id","duplicate_time_id"); intervals=_unique(value["normalized_intervals"],"interval_id","duplicate_interval_id"); relations=_unique(value["temporal_relations"],"relation_id","duplicate_relation_id")
 _unique(value["fact_relations"],"relation_id","duplicate_relation_id");_unique(value["correlation_groups"],"group_id","duplicate_group_id");_unique(value["gaps"],"gap_id","duplicate_gap_id")
 for x in intervals.values():
  if x["start_time_id"] not in times or x["end_time_id"] not in times: raise ValidationFailure("unresolved_time_id")
  if x["earliest_start"]>x["latest_start"] or x["earliest_end"]>x["latest_end"] or x["latest_start"]>x["latest_end"]: raise ValidationFailure("impossible_interval")
  if not set(x["source_fact_ids"])<=facts: raise ValidationFailure("unresolved_fact_id")
 for x in relations.values():
  if x["left_entity_id"] not in intervals or x["right_entity_id"] not in intervals: raise ValidationFailure("unresolved_interval_id")
  if not set(x["supporting_fact_ids"])<=facts: raise ValidationFailure("unresolved_fact_id")
  if not set(x["supporting_evidence_ids"])<=evidence: raise ValidationFailure("unresolved_evidence_id")
  inv=relations.get(x["inverse_relation_id"])
  if not inv: raise ValidationFailure("invalid_inverse_relation_id")
  if inv["relation_type"]!=INVERSE[x["relation_type"]] or inv["inverse_relation_id"]!=x["relation_id"]: raise ValidationFailure("invalid_inverse_relation_type")
 if not _acyclic(value["reconstruction_graph"]["strict_temporal_order"]): raise ValidationFailure("strict_temporal_cycle")
 forbidden={"causes","caused_by","leads_to","consequence_of","attacker_action","compromise_result"}
 if any(x["relation_type"] in forbidden for x in value["temporal_relations"]): raise ValidationFailure("causal_relation_prohibited")
 graph=value["reconstruction_graph"]; seed={k:v for k,v in graph.items() if k not in {"graph_id","canonical_sha256"}}
 if graph["canonical_sha256"]!=sha256_hex(seed): raise ValidationFailure("graph_checksum_mismatch")
 seed={k:v for k,v in value.items() if k not in {"reconstruction_id","canonical_sha256"}}
 if value["canonical_sha256"]!=sha256_hex(seed): raise ValidationFailure("reconstruction_checksum_mismatch")
 return {"valid":True,"temporal_relation_count":len(relations),"fact_relation_count":len(value["fact_relations"]),"correlation_group_count":len(value["correlation_groups"]),"reconstruction_gap_count":len(value["gaps"]),"strict_temporal_cycle_count":0}

def validate_temporal_bundle(bundle:dict[str,Any])->dict[str,Any]:
 if bundle.get("schema_version")!="temporal_reconstruction_bundle_v1": raise ValidationFailure("unknown_schema_version")
 validate_bundle(bundle["source_bundle"])
 if bundle["source_bundle_sha256"]!=sha256_hex(bundle["source_bundle"]): raise ValidationFailure("source_bundle_sha256_mismatch")
 result=validate_temporal_reconstruction(bundle["temporal_reconstruction"],bundle["source_bundle"])
 if bundle["reconstruction_graph"]!=bundle["temporal_reconstruction"]["reconstruction_graph"]: raise ValidationFailure("graph_mismatch")
 if bundle["gaps"]!=bundle["temporal_reconstruction"]["gaps"]: raise ValidationFailure("gap_mismatch")
 semantic=sha256_hex(bundle["temporal_reconstruction"])
 if bundle["manifest"].get("semantic_result_sha256")!=semantic or bundle["checksums"].get("temporal_reconstruction.json")!=semantic: raise ValidationFailure("manifest_semantic_hash_mismatch")
 if not bundle["reproducibility"].get("deterministic_rebuild"): raise ValidationFailure("nondeterministic_rebuild")
 return {"valid":True,**result}
