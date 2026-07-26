"""Официальные синтетические сценарии временной реконструкции v0.4.1."""
from __future__ import annotations
import copy
from typing import Any, Callable
from .builder import build_bundle
from .scenarios import make_event
from .temporal import build_temporal_bundle
from .temporal_validation import validate_temporal_bundle
from .validation import ValidationFailure

POSITIVE_SCENARIOS=(
 "single_exact_fact","strict_before","same_second_precision","overlapping_intervals","contained_interval","meeting_boundaries",
 "out_of_order_events","late_delivery","duplicate_delivery","builder_restart","same_episode_facts","shared_subject_episodes",
 "episodes_without_grouping_basis","attested_clock_domains","unattested_clock_domains","missing_boundary","conflicting_times",
 "insufficient_precision","candidate_cross_episode","explicitly_unrelated","file_order_permutations","delivery_order_permutations",
 "multiple_duplicates","incomplete_evidence_bundle",
)

def _source(scenario_id:str)->dict[str,Any]:
 base="v041-r2-seed-42-"+scenario_id
 first=make_event(base+"-a",timestamp="2026-05-01T10:00:00Z",sequence=1,component_status="healthy")
 second=make_event(base+"-b",timestamp="2026-05-01T10:00:03Z",sequence=2)
 events=[first] if scenario_id=="single_exact_fact" else [first,second]
 if scenario_id in {"same_second_precision","overlapping_intervals","contained_interval","meeting_boundaries","insufficient_precision","conflicting_times"}: second["event_timestamp"]=first["event_timestamp"]
 if scenario_id in {"out_of_order_events","late_delivery","delivery_order_permutations"}: events=[second,first]
 if scenario_id in {"duplicate_delivery","multiple_duplicates"}: events=[first,copy.deepcopy(first),copy.deepcopy(first)]
 if scenario_id=="builder_restart": second["runtime_ref"]["session_id"]="runtime_crash_resume_001"
 if scenario_id in {"same_episode_facts","shared_subject_episodes","attested_clock_domains"}: second["activity_key"]=first["activity_key"]
 incomplete=scenario_id in {"incomplete_evidence_bundle","missing_boundary"}
 return build_bundle(events,"v040_v041_"+scenario_id,incomplete_evidence=incomplete)

def build_positive(scenario_id:str)->dict[str,Any]: return build_temporal_bundle(_source(scenario_id))

def _set(path:tuple[Any,...],value:Any)->Callable[[dict[str,Any]],None]:
 def f(x):
  t=x
  for k in path[:-1]:t=t[k]
  t[path[-1]]=value
 return f
def _append(path:tuple[Any,...],value:Any)->Callable[[dict[str,Any]],None]:
 def f(x):
  t=x
  for k in path:t=t[k]
  t.append(copy.deepcopy(value))
 return f

def negative_cases()->list[tuple[str,str,Callable[[dict[str,Any]],None]]]:
 b=build_positive("strict_before"); r=b["temporal_reconstruction"]; t=r["normalized_times"][0]; i=r["normalized_intervals"][0]; rel=r["temporal_relations"][0]; fr=r["fact_relations"][0]; g=r["correlation_groups"][0]; gap=r["gaps"][0]
 cases=[
 ("neg_001_time_without_source","schema_validation_failed",_set(("temporal_reconstruction","normalized_times",0,"source_evidence_ids"),None)),
 ("neg_002_negative_uncertainty","schema_validation_failed",_set(("temporal_reconstruction","normalized_times",0,"uncertainty_before_ms"),-1)),
 ("neg_003_unknown_precision","schema_validation_failed",_set(("temporal_reconstruction","normalized_times",0,"precision"),"nanosecond")),
 ("neg_004_impossible_interval","impossible_interval",_set(("temporal_reconstruction","normalized_intervals",0,"latest_start"),"2030-01-01T00:00:00.000Z")),
 ("neg_005_end_before_start","impossible_interval",_set(("temporal_reconstruction","normalized_intervals",0,"latest_end"),"2020-01-01T00:00:00.000Z")),
 ("neg_006_unresolved_time","unresolved_time_id",_set(("temporal_reconstruction","normalized_intervals",0,"start_time_id"),"time_"+"f"*64)),
 ("neg_007_unresolved_interval","unresolved_interval_id",_set(("temporal_reconstruction","temporal_relations",0,"left_entity_id"),"int_"+"f"*64)),
 ("neg_008_unresolved_fact","unresolved_fact_id",_set(("temporal_reconstruction","temporal_relations",0,"supporting_fact_ids"),["fact_"+"f"*64])),
 ("neg_009_unresolved_evidence","unresolved_evidence_id",_set(("temporal_reconstruction","temporal_relations",0,"supporting_evidence_ids"),["evr_"+"f"*64])),
 ("neg_010_unknown_relation_type","schema_validation_failed",_set(("temporal_reconstruction","temporal_relations",0,"relation_type"),"unknown")),
 ("neg_011_causal_relation","schema_validation_failed",_set(("temporal_reconstruction","temporal_relations",0,"relation_type"),"causes")),
 ("neg_012_bad_inverse_id","invalid_inverse_relation_id",_set(("temporal_reconstruction","temporal_relations",0,"inverse_relation_id"),"trel_"+"f"*64)),
 ("neg_013_bad_inverse_type","invalid_inverse_relation_type",_set(("temporal_reconstruction","temporal_relations",1,"relation_type"),"overlaps")),
 ("neg_014_relation_without_basis","schema_validation_failed",_set(("temporal_reconstruction","temporal_relations",0,"derivation_basis"),"")),
 ("neg_015_relation_without_support","schema_validation_failed",_set(("temporal_reconstruction","temporal_relations",0,"supporting_fact_ids"),[])),
 ("neg_016_duplicate_relation","duplicate_relation_id",_append(("temporal_reconstruction","temporal_relations"),rel)),
 ("neg_017_duplicate_group","duplicate_group_id",_append(("temporal_reconstruction","correlation_groups"),g)),
 ("neg_018_duplicate_gap","duplicate_gap_id",_append(("temporal_reconstruction","gaps"),gap)),
 ("neg_019_duplicate_time","duplicate_time_id",_append(("temporal_reconstruction","normalized_times"),t)),
 ("neg_020_duplicate_interval","duplicate_interval_id",_append(("temporal_reconstruction","normalized_intervals"),i)),
 ("neg_021_bad_graph_hash","graph_checksum_mismatch",_set(("temporal_reconstruction","reconstruction_graph","canonical_sha256"),"f"*64)),
 ("neg_022_bad_reconstruction_hash","reconstruction_checksum_mismatch",_set(("temporal_reconstruction","canonical_sha256"),"f"*64)),
 ("neg_023_source_bundle_hash","source_bundle_sha256_mismatch",_set(("source_bundle_sha256",),"f"*64)),
 ("neg_024_unknown_bundle_schema","unknown_schema_version",_set(("schema_version",),"temporal_reconstruction_bundle_v2")),
 ("neg_025_manifest_semantic_hash","manifest_semantic_hash_mismatch",_set(("manifest","semantic_result_sha256"),"f"*64)),
 ("neg_026_checksum_semantic_hash","manifest_semantic_hash_mismatch",_set(("checksums","temporal_reconstruction.json"),"f"*64)),
 ("neg_027_nondeterministic_rebuild","nondeterministic_rebuild",_set(("reproducibility","deterministic_rebuild"),False)),
 ("neg_028_unknown_candidate","candidate_id_mismatch",_set(("source_bundle","passive_events",0,"candidate_ref","candidate_id"),"v99999:ffffffffffffffff")),
 ("neg_029_candidate_substitution","schema_validation_failed",_set(("source_bundle","incident_card","candidate_id"),"v99999:ffffffffffffffff")),
 ("neg_030_event_contract_substitution","invalid_passive_event",_set(("source_bundle","passive_events",0,"event_contract_version"),"shadow_event_v1")),
 ("neg_031_duplicate_event_changed","duplicate_event_id_content_mismatch",lambda x:x["source_bundle"]["passive_events"].append({**copy.deepcopy(x["source_bundle"]["passive_events"][0]),"event_timestamp":"2027-01-01T00:00:00Z"})),
 ("neg_032_source_manifest_corrupt","manifest_semantic_hash_mismatch",_set(("source_bundle","manifest","semantic_result_sha256"),"f"*64)),
 ]
 # Дополнительные конкретные нарушения повторяют независимые поля строгих контрактов.
 extras=[
 ("time_validation_status",("temporal_reconstruction","normalized_times",0,"validation_status"),"invalid","schema_validation_failed"),
 ("time_clock_domain",("temporal_reconstruction","normalized_times",0,"clock_domain"),"","schema_validation_failed"),
 ("interval_status",("temporal_reconstruction","normalized_intervals",0,"interval_status"),"invalid","schema_validation_failed"),
 ("relation_certainty",("temporal_reconstruction","temporal_relations",0,"relation_certainty"),"absolute","schema_validation_failed"),
 ("relation_derived",("temporal_reconstruction","temporal_relations",0,"derived"),"yes","schema_validation_failed"),
 ("fact_relation_type",("temporal_reconstruction","fact_relations",0,"relation_type"),"same_model_class","schema_validation_failed"),
 ("fact_relation_basis",("temporal_reconstruction","fact_relations",0,"relation_basis"),"","schema_validation_failed"),
 ("fact_relation_certainty",("temporal_reconstruction","fact_relations",0,"certainty"),"proven","schema_validation_failed"),
 ("group_rule_missing",("temporal_reconstruction","correlation_groups",0,"grouping_rule_id"),"","schema_validation_failed"),
 ("group_status",("temporal_reconstruction","correlation_groups",0,"status"),"confirmed_incident","schema_validation_failed"),
 ("gap_type",("temporal_reconstruction","gaps",0,"gap_type"),"invented_fact","schema_validation_failed"),
 ("gap_missing_information",("temporal_reconstruction","gaps",0,"missing_information"),[],"schema_validation_failed"),
 ("gap_basis",("temporal_reconstruction","gaps",0,"basis"),"","schema_validation_failed"),
 ("gap_manual_check",("temporal_reconstruction","gaps",0,"suggested_manual_check"),"","schema_validation_failed"),
 ("time_bad_id",("temporal_reconstruction","normalized_times",0,"time_id"),"time_bad","schema_validation_failed"),
 ("interval_bad_id",("temporal_reconstruction","normalized_intervals",0,"interval_id"),"int_bad","schema_validation_failed"),
 ("relation_bad_id",("temporal_reconstruction","temporal_relations",0,"relation_id"),"trel_bad","schema_validation_failed"),
 ("fact_relation_bad_id",("temporal_reconstruction","fact_relations",0,"relation_id"),"frel_bad","schema_validation_failed"),
 ("group_bad_id",("temporal_reconstruction","correlation_groups",0,"group_id"),"grp_bad","schema_validation_failed"),
 ("gap_bad_id",("temporal_reconstruction","gaps",0,"gap_id"),"gap_bad","schema_validation_failed"),
 ("graph_bad_id",("temporal_reconstruction","reconstruction_graph","graph_id"),"graph_bad","schema_validation_failed"),
 ("graph_bad_sha",("temporal_reconstruction","reconstruction_graph","canonical_sha256"),"bad","schema_validation_failed"),
 ("unknown_time_field",("temporal_reconstruction","normalized_times",0,"unexpected"),True,"schema_validation_failed"),
 ("unknown_interval_field",("temporal_reconstruction","normalized_intervals",0,"unexpected"),True,"schema_validation_failed"),
 ("unknown_relation_field",("temporal_reconstruction","temporal_relations",0,"unexpected"),True,"schema_validation_failed"),
 ("unknown_gap_field",("temporal_reconstruction","gaps",0,"unexpected"),True,"schema_validation_failed"),
 ("unknown_group_field",("temporal_reconstruction","correlation_groups",0,"unexpected"),True,"schema_validation_failed"),
 ("unknown_fact_relation_field",("temporal_reconstruction","fact_relations",0,"unexpected"),True,"schema_validation_failed"),
 ]
 for n,p,v,e in extras: cases.append((f"neg_{len(cases)+1:03d}_{n}",e,_set(p,v)))
 return cases

def run_campaign()->dict[str,Any]:
 positive=[]
 for sid in POSITIVE_SCENARIOS:
  bundle=build_positive(sid); result=validate_temporal_bundle(bundle)
  positive.append({"scenario_id":sid,"passed":result["valid"],"semantic_sha256":bundle["temporal_reconstruction"]["canonical_sha256"]})
 negative=[]
 for sid,expected,mutation in negative_cases():
  bundle=build_positive("strict_before");mutation(bundle);actual=None
  try:validate_temporal_bundle(bundle)
  except ValidationFailure as error:actual=error.code
  negative.append({"scenario_id":sid,"expected_error_code":expected,"actual_error_code":actual,"rejected":actual==expected})
 return {"schema_version":"v0_4_1_campaign_result_v1","positive":positive,"negative":negative,"positive_scenario_count":len(positive),"positive_scenario_passed_count":sum(x["passed"] for x in positive),"negative_scenario_count":len(negative),"negative_scenario_rejected_count":sum(x["rejected"] for x in negative)}
