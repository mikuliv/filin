"""Формирование строгих версионированных JSON Schema v0.4.2."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]/"incident_reconstruction/contracts/v0_4_2"
S={
"hypothesis_rule_v1":"rule_id rule_revision question_type hypothesis_type hypothesis_title_template hypothesis_statement_template applicable_scope_types required_fact_types required_temporal_relation_types required_fact_relation_types optional_fact_types forbidden_conditions supporting_evidence_rules contradicting_evidence_rules critical_gap_types alternative_rule_ids confirmation_conditions falsification_conditions limitations_template deterministic_priority enabled",
"analytical_question_v1":"question_id question_type question_text scope_id basis_fact_ids basis_relation_ids basis_group_ids basis_gap_ids applicable_rule_ids limitations",
"hypothesis_scope_v1":"scope_id scope_type subject_ids event_ids episode_ids correlation_group_ids time_interval_ids question_id limitations",
"hypothesis_evidence_assessment_v1":"assessment_id hypothesis_id source_entity_type source_entity_id direction evidence_kind directness relevance duplication_group_id assessment_rule_id explanation_code limitations",
"incident_hypothesis_v2":"hypothesis_id rule_id question_id scope_id hypothesis_type title statement status supporting_assessment_ids contradicting_assessment_ids neutral_assessment_ids critical_gap_ids noncritical_gap_ids alternative_hypothesis_ids comparison_ids confirmation_conditions falsification_conditions missing_information analyst_question_ids evidential_profile limitations canonical_sha256",
"evidential_profile_v1":"profile_id hypothesis_id direct_support_count derived_support_count contextual_support_count direct_contradiction_count derived_contradiction_count critical_gap_count noncritical_gap_count unique_support_source_count unique_contradiction_source_count duplicated_source_count profile_status derivation_rule_id limitations",
"hypothesis_comparison_v1":"comparison_id question_id scope_id left_hypothesis_id right_hypothesis_id comparison_result comparison_basis decisive_assessment_ids unresolved_difference_ids limitations inverse_comparison_id canonical_sha256",
"hypothesis_set_v1":"hypothesis_set_id question_id scope_id hypothesis_ids comparison_ids retained_hypothesis_ids contradicted_hypothesis_ids unresolved_hypothesis_ids review_priority_hypothesis_ids forced_winner set_status missing_information analyst_question_ids limitations canonical_sha256",
"analyst_question_v1":"analyst_question_id question_id scope_id related_hypothesis_ids source_gap_ids question_type question_text expected_evidence_type effect_if_confirmed effect_if_refuted requires_human_review execution_status limitations",
"hypothesis_explanation_v1":"explanation_id hypothesis_id rule_id question_id scope_id supporting_items contradicting_items missing_items status_derivation comparison_summary template_code limitations canonical_sha256",
"hypothesis_assessment_record_v1":"record_id hypothesis_set_id assessed_at_mode input_bundle_sha256 rule_catalog_sha256 hypothesis_ids comparison_ids unresolved_questions no_final_determination automatic_action_performed limitations canonical_sha256",
"hypothesis_analysis_v1":"analysis_id source_temporal_bundle_id source_temporal_bundle_sha256 analytical_questions hypothesis_sets hypotheses evidence_assessments evidential_profiles comparisons analyst_questions explanations assessment_records analysis_status deterministic_build limitations canonical_sha256",
"hypothesis_analysis_bundle_v1":"manifest source_temporal_bundle_sha256 source_temporal_bundle rule_catalog rule_catalog_sha256 hypothesis_analysis explanations build_journal builder_version standalone_verification policy_result checksums reproducibility limitations"}
ENUMS={"status":["unsupported","possible","partially_supported","supported_within_available_evidence","contradicted","indeterminate"],"comparison_result":["better_supported","less_supported","equally_supported","incomparable","insufficient_data","not_comparable"],"execution_status":["not_executed"],"direction":["supports","contradicts","neutral","context_only","missing_expected_information"],"directness":["directly_observed","deterministically_derived","contextual","unavailable"]}
def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 for name,rawfields in S.items():
  fields=rawfields.split();props={"schema_version":{"const":name}}
  for f in fields:
   if f in ENUMS:props[f]={"enum":ENUMS[f]}
   elif f in {"forced_winner","automatic_action_performed"}:props[f]={"const":False}
   elif f in {"requires_human_review","no_final_determination","deterministic_build","enabled"}:props[f]={"type":"boolean"}
   elif f.endswith("count") or f in {"rule_revision","deterministic_priority"}:props[f]={"type":"integer","minimum":0}
   elif f.endswith("ids") or f in {"limitations","missing_information","supporting_items","contradicting_items","missing_items","comparison_summary","unresolved_questions"}:props[f]={"type":"array","items":{"type":"string"},"uniqueItems":True}
   elif f.endswith("sha256"):props[f]={"type":"string","pattern":"^[a-f0-9]{64}$"}
   elif f in {"manifest","rule_catalog","source_temporal_bundle","hypothesis_analysis","policy_result","checksums","reproducibility","evidential_profile"}:props[f]={"type":"object"}
   else:props[f]={"type":"string","minLength":1}
  if name=="analyst_question_v1":props["requires_human_review"]={"const":True}
  if name=="hypothesis_assessment_record_v1":props["no_final_determination"]={"const":True}
  schema={"$schema":"https://json-schema.org/draft/2020-12/schema","$id":f"https://filin.local/contracts/v0_4_2/{name}","type":"object","additionalProperties":False,"required":["schema_version",*fields],"properties":props}
  (ROOT/f"{name}.schema.json").write_text(json.dumps(schema,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
 print(len(S))
if __name__=="__main__":main()
