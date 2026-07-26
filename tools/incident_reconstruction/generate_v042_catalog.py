"""Однократное формирование декларативного frozen-каталога правил v0.4.2."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"incident_reconstruction/rules/v0_4_2_hypothesis_rules_v1.json"
EXPLANATIONS={
"auth_failures":["possible_credential_guessing","user_password_error","stale_service_credentials","integration_configuration_error","insufficient_data"],
"beacon":["possible_periodic_control","routine_health_check","scheduled_update","system_monitoring","periodic_application_request","insufficient_data"],
"low_rate_dos":["possible_resource_exhaustion","erroneous_request_retry","faulty_client","service_performance_problem","normal_load_insufficient_capacity","insufficient_data"],
"port_scan":["possible_reconnaissance","administrative_inventory","vulnerability_assessment","network_diagnostics","configuration_error","insufficient_data"],
"web_probe":["possible_web_reconnaissance","availability_monitoring","search_crawler","quality_testing","integration_error","insufficient_data"],
"benign":["routine_activity","insufficient_suspicious_basis"]}
def main():
 rules=[]
 for question,types in EXPLANATIONS.items():
  for priority,kind in enumerate(types):
   base={"schema_version":"hypothesis_rule_v1","rule_id":f"rule_{question}_{kind}_r1","rule_revision":1,"question_type":question,"hypothesis_type":kind,"hypothesis_title_template":f"Гипотеза: {kind}","hypothesis_statement_template":f"Наблюдения допускают объяснение {kind}; это не установленный факт.","applicable_scope_types":["correlation_group"],"required_fact_types":[],"required_temporal_relation_types":[],"required_fact_relation_types":[],"optional_fact_types":["model_output","network_observation","source_integrity"],"forbidden_conditions":["confirmed_compromise","automatic_action"],"supporting_evidence_rules":["independent_observed_fact"],"contradicting_evidence_rules":["healthy_source_or_alternative_context"],"critical_gap_types":["incomplete_evidence","conflicting_timestamp"],"alternative_rule_ids":[],"confirmation_conditions":["Получить независимое наблюдаемое подтверждение."],"falsification_conditions":["Получить наблюдаемое противоречащее сведение."],"limitations_template":["Гипотеза применима только к лабораторной области рассмотрения."],"deterministic_priority":priority,"enabled":True}
   rules.append(base)
 ids=[x["rule_id"] for x in rules]
 for x in rules:x["alternative_rule_ids"]=[i for i in ids if i.startswith("rule_"+x["question_type"]+"_") and i!=x["rule_id"]]
 value={"schema_version":"hypothesis_rule_catalog_v1","stage":"v0.4.2","frozen":True,"rule_count":len(rules),"rules":rules}
 raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()+b"\n";OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_bytes(raw);print(len(rules),hashlib.sha256(raw).hexdigest())
if __name__=="__main__":main()
