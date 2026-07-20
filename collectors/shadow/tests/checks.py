import json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; REPORT=ROOT/'ml/reports/v0_3_14'
def load(name): return json.loads((REPORT/name).read_text(encoding='utf-8'))
def check(slug):
    policy=load('v0_3_14_policy_result.json'); assert policy['v0314_shadow_readiness_passed']
    if any(x in slug for x in ('event_','schema','privacy','forbidden','size','canonicalization','identity')):
        schema=load('schema_validation.json'); assert schema['event_schema_validation_passed'] and schema['invalid_fixture_rejected_count']==schema['invalid_fixture_count']
        assert load('privacy_audit.json')['privacy_audit_passed']
    if any(x in slug for x in ('queue','priority','backpressure')):
        q=load('queue_audit.json'); assert q['queue_policy_passed'] and q['queue_peak']<=q['queue_capacity'] and q['alert_priority_preserved']
    if 'spool' in slug: assert load('spool_recovery.json')['spool_recovery_passed']
    if any(x in slug for x in ('sink','duplicate','timeout','connection_reset','schema_reject','unknown_ack','exporter')):
        i=load('idempotency_audit.json'); assert i['idempotency_policy_passed'] and i['semantic_duplicate_count']==0
    if any(x in slug for x in ('retry','rate_limit','graceful')): assert policy['retry_policy_passed'] and policy['rate_limit_policy_passed']
    if 'hash_chain' in slug: assert load('hash_chain_audit.json')['event_hash_chain_passed']
