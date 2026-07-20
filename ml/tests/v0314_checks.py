import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; REPORT=ROOT/'ml/reports/v0_3_14'
def load(name): return json.loads((REPORT/name).read_text(encoding='utf-8'))
def check(slug):
 p=load('v0_3_14_policy_result.json'); assert p['v0314_shadow_readiness_completed'] and p['v0314_shadow_readiness_passed']
 if any(x in slug for x in ('protocol','candidate','positive_control')): assert load('v0313_positive_control.json')['mismatches']=={}
 if 'checkpoint' in slug: assert load('v0313_checkpoint_consistency_audit.json')['v0313_checkpoint_evidence_consistency_passed']
 if 'no_model' in slug: assert load('no_model_intervention_audit.json')['predict_call_count']==load('no_model_intervention_audit.json')['fit_call_count']==0
 if any(x in slug for x in ('production','backend_write','automatic_action','fail_safe')): assert p['production_connection_attempt_count']==p['backend_write_attempt_count']==p['automatic_action_attempt_count']==0
 if any(x in slug for x in ('replay','causal','source_reconciliation')): assert load('replay_equivalence.json')['all_replay_profiles_semantically_equivalent'] and load('source_reconciliation.json')['source_event_reconciliation_passed']
 if 'fault' in slug or 'crash' in slug: assert load('fault_campaign_result.json')['all_fault_scenarios_passed'] and load('crash_consistency.json')['crash_consistency_passed']
 if 'backend_contract' in slug: assert load('backend_contract_gap_analysis.json')['blocking_security_gap_count']==0
 if 'logging' in slug: assert load('logging_redaction_audit.json')['logging_redaction_passed']
 if 'observability' in slug: assert load('observability_audit.json')['observability_policy_passed']
 if 'performance' in slug or 'resource' in slug or 'load_test' in slug: assert load('performance_preflight.json')['performance_policy_passed'] and load('load_test_result.json')['load_test_passed']
 if 'summary' in slug: assert '# Филин v0.3.14' in (REPORT/'v0_3_14_summary.md').read_text(encoding='utf-8')
