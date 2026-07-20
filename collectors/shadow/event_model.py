from __future__ import annotations
from collections import defaultdict
from .canonical import canonical_bytes, deterministic_id, sha256

SCHEMA="shadow_event_v1"; CANDIDATE="v0311:19176acb401be2d4"

def causal_sort(records):
    required=("benchmark_id","run_id","activity_key","causal_order","immutable_row_id")
    if any(any(row.get(k) is None for k in required) for row in records): raise ValueError("causal_mapping_incomplete")
    return sorted(records,key=lambda row:(row["benchmark_id"],row["run_id"],row["activity_key"],row["causal_order"],row["immutable_row_id"]))

def _base(row,event_type,bundle_hash,prediction_hash,sequence,observed_at="1970-01-01T00:00:00Z"):
    identity=(SCHEMA,CANDIDATE,prediction_hash,row["immutable_row_id"],event_type,row["causal_order"],row["primary_state"])
    event_id=deterministic_id(identity)
    return {"schema_version":SCHEMA,"event_type":event_type,"event_id":event_id,"idempotency_key":deterministic_id(("delivery",)+identity),"event_created_at":observed_at,"event_observed_at":observed_at,"source_component":"filin_passive_exporter","source_version":"v0.3.14","candidate_id":CANDIDATE,"candidate_manifest_sha256":"ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c","source_bundle_sha256":bundle_hash,"source_prediction_sha256":prediction_hash,"source_row_id":row["immutable_row_id"],"source_run_id_hash":deterministic_id(("run",row["run_id"])),"activity_key_hash":deterministic_id(("activity",row["activity_key"])),"causal_order":int(row["causal_order"]),"event_sequence":sequence,"primary_state":row["primary_state"],"event_hash":"0"*64,"previous_event_hash":None,"action_authority":"none","enforcement_allowed":False}

def generate(records,bundle_hash,prediction_hash):
    ordered=causal_sort(records); events=[]; continuations=defaultdict(list)
    for row in ordered:
        summary={"top_class":row["top_class"],"top_probability":row["top_probability"],"benign_probability":row["benign_probability"],"margin":row["margin"],"conformal_set":row["conformal_set"],"candidate_evidence":row["candidate_evidence"],"strong_evidence":row["strong_evidence"],"weak_evidence":row["weak_evidence"]}
        events.append({**_base(row,"decision_observation",bundle_hash,prediction_hash,0),**summary})
        state=row["primary_state"]
        if state.startswith("alert_emitted:"):
            klass=state.split(":",1)[1]; alert_id=deterministic_id(("alert",row["run_id"],row["activity_key"],klass,row["causal_order"]))
            events.append({**_base(row,"alert_emitted",bundle_hash,prediction_hash,1),"alert_event_id":alert_id,"alert_class":klass,"alert_first_seen_causal_order":row["causal_order"],"dedup_key_hash":deterministic_id(("dedup",row["dedup_key"])),"duplicate_suppressed":False,"transition_reason":row["transition_reason"]})
        elif state.startswith("review_required:"):
            events.append({**_base(row,"review_required",bundle_hash,prediction_hash,1),"review_reason":row["transition_reason"]})
        elif state.startswith("post_alert_continuation:"):
            continuations[(row["run_id"],row["activity_key"],state.split(":",1)[1])].append(row)
    for (_run,_activity,klass),rows in continuations.items():
        row=rows[0]; events.append({**_base(row,"alert_continuation",bundle_hash,prediction_hash,2),"alert_class":klass,"continuation_count":len(rows),"continuation_first_causal_order":min(r["causal_order"] for r in rows),"continuation_last_causal_order":max(r["causal_order"] for r in rows),"duplicate_suppressed":True,"transition_reason":"aggregated_post_alert_continuation"})
    events.sort(key=lambda e:(e["source_bundle_sha256"],e["source_run_id_hash"],e["activity_key_hash"],e["causal_order"],e["event_sequence"],e["source_row_id"]))
    previous={}
    for event in events:
        key=event["activity_key_hash"]; event["previous_event_hash"]=previous.get(key); event["event_hash"]=sha256(canonical_bytes(event)); previous[key]=event["event_hash"]
    return events
