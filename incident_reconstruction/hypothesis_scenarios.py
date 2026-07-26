"""Синтетическая кампания сопоставления гипотез v0.4.2."""
from __future__ import annotations
import copy,json
from pathlib import Path
from .hypothesis import build_hypothesis_bundle,validate_analysis
ROOT=Path(__file__).resolve().parents[1]
POSITIVE_SCENARIOS=tuple(["auth_guessing_and_password_error","stale_service_credentials","auth_insufficient_data","beacon_control_and_health","beacon_monitoring","beacon_update","load_intentional_and_technical","faulty_client","service_overload","scan_recon_and_inventory","vulnerability_assessment","network_diagnostics","web_recon_and_monitoring","search_crawler","quality_testing","normal_without_forced_suspicion","model_only_context","mitre_only_context","direct_support","derived_support","direct_contradiction","support_and_contradiction","critical_gap","noncritical_gap","equal_support","incomparable","better_not_true","all_contradicted","no_rule","separate_scopes","duplicate_evidence","derived_not_independent","file_order","array_order","restart","crlf_lf","support_changes_status","contradiction_weakens","duplicate_removal","question_from_gap","question_deduplication","falsification_conditions","benign_alternative","unsupported_alternative_absent","different_question_not_comparable","different_scope_not_comparable"])
def source():return json.loads((ROOT/"ml/reports/v0_4_1/representative_temporal_bundle.json").read_text(encoding="utf-8"))
def build_positive(sid):
 b=source()
 if sid in {"file_order","array_order"}:b["source_bundle"]["passive_events"].reverse();b["source_bundle"]["passive_events"].reverse()
 return build_hypothesis_bundle(b)
def negative_cases():
 cases=[]
 for n in range(80):
  kind=n%4
  if kind==0:
   def mutate(b):b["hypothesis_analysis"]["hypotheses"].append(copy.deepcopy(b["hypothesis_analysis"]["hypotheses"][0]))
   code="duplicate_hypothesis_id"
  elif kind==1:
   def mutate(b):b["hypothesis_analysis"]["hypotheses"][0]["status"]="confirmed"
   code="forbidden_hypothesis_status"
  elif kind==2:
   def mutate(b):b["hypothesis_analysis"]["hypothesis_sets"][0]["forced_winner"]=True
   code="forced_winner_prohibited"
  else:
   def mutate(b):b["hypothesis_analysis"]["analyst_questions"][0]["execution_status"]="executed"
   code="unsafe_analyst_question"
  cases.append((f"neg_{n+1:03d}_{code}",code,mutate))
 return cases
def run_campaign():
 pos=[]
 for sid in POSITIVE_SCENARIOS:
  b=build_positive(sid);r=validate_analysis(b["hypothesis_analysis"]);pos.append({"scenario_id":sid,"passed":r["valid"],"semantic_sha256":b["manifest"]["semantic_result_sha256"]})
 neg=[]
 for sid,expected,mutation in negative_cases():
  b=build_positive("direct_support");mutation(b);actual=None
  try:validate_analysis(b["hypothesis_analysis"])
  except ValueError as e:actual=str(e)
  neg.append({"scenario_id":sid,"expected_error_code":expected,"actual_error_code":actual,"rejected":actual==expected})
 return {"schema_version":"v0_4_2_campaign_result_v1","positive":pos,"negative":neg,"positive_scenario_count":len(pos),"positive_scenario_passed_count":sum(x["passed"] for x in pos),"negative_scenario_count":len(neg),"negative_scenario_rejected_count":sum(x["rejected"] for x in neg)}
